"""Public deterministic IA-HASH 1.2 vectors; never use this seed operationally.

Run from the repository: python tools/verify_legacy_vectors.py.
Optional --crypto-path and --vectors select local copies explicitly.
--write refreshes the selected vector file; otherwise verifies it.
Loads the actual baseline crypto.py without importing the package/DB/network.
The seed is RFC 8032 section 7.1 TEST 1, intentionally public test material.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
import unicodedata

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--crypto-path", type=Path, default=ROOT / "iahash" / "crypto.py")
parser.add_argument("--vectors", type=Path, default=ROOT / "docs" / "vectors" / "legacy-v1.2.json")
parser.add_argument("--write", action="store_true", help="Regenerate only the selected public vector JSON")
args = parser.parse_args()
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

MODULE_PATH = args.crypto_path.resolve()
spec = importlib.util.spec_from_file_location("iahash_legacy_vector_crypto", MODULE_PATH)
assert spec is not None and spec.loader is not None
crypto = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = crypto
spec.loader.exec_module(crypto)

PUBLIC_TEST_SEED_HEX = "9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60"
private_key = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(PUBLIC_TEST_SEED_HEX))
public_key = private_key.public_key()
public_bytes = public_key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
assert public_bytes.hex() == "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"

texts = [None, "", "Cafe\u0301 \t\r\nsegunda\r\n\t\n", "A\u00a0\n", "\nA\n\n"]
normalization = [
    {
        "input": text,
        "normalized": crypto.normalize_text(text),
        "utf8_hex": crypto.normalized_bytes(text).hex(),
        "sha256": crypto.sha256_hex(crypto.normalized_bytes(text)),
    }
    for text in texts
]
assert normalization[2]["normalized"] == "Caf\u00e9\nsegunda"
assert normalization[2]["sha256"] == "64d5495c55faf387082751b6c052adbcd7a65af84dc94c5e2ecf54854a379aba"
assert normalization[3]["normalized"] == "A\u00a0"
assert normalization[4]["normalized"] == "\nA"

def make_vector(prompt: str, response: str, model: str, timestamp: str) -> dict:
    hashes = crypto.compute_pair_hashes(
        prompt, response, protocol_version="IAHASH-1.2", prompt_id=None,
        model=model, timestamp=timestamp,
    )
    preimage = "|".join([
        "IAHASH-1.2", "", hashes.h_prompt, hashes.h_response, model, timestamp,
    ])
    message = hashes.h_total.encode("utf-8")
    signature = crypto.sign_message(message, private_key)
    assert crypto.sha256_hex(preimage.encode("utf-8")) == hashes.h_total
    assert len(message) == 64 and len(signature) == 64
    assert crypto.verify_signature(message, signature, public_key)
    assert not crypto.verify_signature(bytes.fromhex(hashes.h_total), signature, public_key)
    altered_signature = bytes([signature[0] ^ 1]) + signature[1:]
    assert not crypto.verify_signature(message, altered_signature, public_key)
    altered_message = bytes([message[0] ^ 1]) + message[1:]
    assert not crypto.verify_signature(altered_message, signature, public_key)
    wrong_key = Ed25519PrivateKey.from_private_bytes(bytes(range(32))).public_key()
    assert not crypto.verify_signature(message, signature, wrong_key)
    return {
        "prompt": prompt, "response": response,
        "protocol_version": "IAHASH-1.2", "prompt_id": None,
        "model": model, "timestamp": timestamp,
        "h_prompt": hashes.h_prompt, "h_response": hashes.h_response,
        "h_total_preimage": preimage, "h_total": hashes.h_total,
        "signed_message_utf8_hex": message.hex(), "signature_hex": signature.hex(),
        "iah_id": crypto.derive_iah_id(hashes.h_total),
        "checks": {
            "valid_signature": True, "altered_signature_rejected": True,
            "altered_message_rejected": True, "wrong_key_rejected": True,
            "binary_digest_as_message_rejected": True,
        },
    }

unicode_pair = make_vector(texts[2], "Re\u0301ponse\r\nOK\t\n\n", "test-model", "2026-10-10T12:00:00Z")
collision_a = make_vector("A", "B", "gpt-x|extra", "2026-10-10T12:00:00Z")
collision_b = make_vector("A", "B", "gpt-x", "extra|2026-10-10T12:00:00Z")
assert collision_a["h_total"] == collision_b["h_total"]
assert collision_a["signature_hex"] == collision_b["signature_hex"]
assert collision_a["iah_id"] == "644tCxbwWfCLxt25"

result = {
    "warning": "PUBLIC TEST SEED ONLY. Never use this private seed for LAB/STAGING/PRODUCTION issuance.",
    "format": "IAHASH-1.2 historical crypto vectors; not a new protocol implementation",
    "source": {"repository": "IAHASH/iahash", "branch": "v1.2", "commit": "96922745e9062b752c163420d4274215f5a6b3ab", "file": "iahash/crypto.py"},
    "unicode_database": unicodedata.unidata_version,
    "public_test_seed_hex": PUBLIC_TEST_SEED_HEX,
    "public_key_raw_hex": public_bytes.hex(),
    "normalization": normalization,
    "unicode_pair": unicode_pair,
    "delimiter_ambiguity": {"first": collision_a, "second": collision_b, "same_signed_message_and_signature": True},
}
output_path = args.vectors.resolve()
if args.write:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
else:
    expected = json.loads(output_path.read_text(encoding="utf-8"))
    # The declared Unicode runtime may differ; each byte/hash/signature must agree.
    result.pop("unicode_database")
    expected.pop("unicode_database")
    assert result == expected, "Historical public vector changed"
print("PASS: actual legacy crypto, normalization, signed hex, wrong key/tamper, delimiter ambiguity")
