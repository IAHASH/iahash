"""Public vectors and adversarial checks for the standalone reference Core."""
from copy import deepcopy
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

import iahash_core as core

PUBLIC_TEST_SEED = "9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60"
RECEIPT_ID = "123e4567-e89b-42d3-a456-426614174000"
RECEIVED_AT = "2026-10-10T12:00:00.000000Z"
ISSUER = "iahash:public-test-vector"
ORIGINALS = {"par1": {"text": "Cafe\u0301 \t\r\nsegunda\r\n\t\n"}, "par2": {"base64": "AP8K"}}


def signing_key():
    return Ed25519PrivateKey.from_private_bytes(bytes.fromhex(PUBLIC_TEST_SEED))


def pair():
    return core.make_pair(ORIGINALS["par1"]["text"], b"\x00\xff\n", profile2=core.BYTES_PROFILE)


def receipt():
    return core.sign_receipt(pair(), signing_key(), issuer_id=ISSUER, environment="LAB", receipt_id=RECEIPT_ID, received_at=RECEIVED_AT)


def trust():
    public_key = signing_key().public_key()
    return {(ISSUER, "LAB", core.key_id(public_key)): public_key}


def check(certificate=None, **kwargs):
    return core.verify_receipt(receipt() if certificate is None else certificate, trusted_keys=kwargs.pop("trusted_keys", trust()), expected_environment=kwargs.pop("expected_environment", "LAB"), **kwargs)


def vector_document():
    certificate = receipt()
    public_bytes = signing_key().public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return {
        "warning": "PUBLIC TEST SEED ONLY. This key has no issuer authority; never use it for operational issuance.",
        "protocol_version": core.PROTOCOL_VERSION,
        "unicode_database": core.UNICODE_VERSION,
        "public_test_seed_hex": PUBLIC_TEST_SEED,
        "public_key_raw_hex": public_bytes.hex(),
        "originals": ORIGINALS,
        "normalized_par1_utf8_hex": "436166c3a90a736567756e6461",
        "par2_bytes_hex": "00ff0a",
        "pair": pair(),
        "pair_preimage_hex": (core.PAIR_DOMAIN + core.canonical_bytes(pair())).hex(),
        "pair_id": core.derive_pair_id(pair()),
        "certificate": certificate,
        "signed_message_hex": (core.CERTIFICATE_DOMAIN + core.canonical_bytes(certificate["body"])).hex(),
        "expected_without_originals": "VERIFIED_RECEIPT",
        "expected_with_originals": "VERIFIED_CONTENT",
    }


def test_public_vector_matches_exact_bytes_and_signatures():
    saved = json.loads((Path(__file__).resolve().parents[1] / "docs/vectors/pair-v1.json").read_text(encoding="utf-8"))
    assert vector_document() == saved
    assert check(saved["certificate"])["status"] == "VERIFIED_RECEIPT"
    assert check(saved["certificate"], originals=saved["originals"])["status"] == "VERIFIED_CONTENT"
    # Direct library verification independently of the Core verification path.
    signing_key().public_key().verify(bytes.fromhex(saved["certificate"]["signature"]), bytes.fromhex(saved["signed_message_hex"]))
    assert hashlib.sha256(bytes.fromhex(saved["pair_preimage_hex"])).hexdigest() == saved["pair_id"]


@pytest.mark.parametrize(("raw", "expected"), [
    ("", ""), ("\n\r\n\t \r", ""),
    ("Cafe\u0301 \t\r\nsegunda\r\n\t\n", "Caf\u00e9\nsegunda"),
    ("\n A  \rB\t\n", "\n A\nB"),
    ("A\u00a0\n", "A\u00a0"), ("\ufeffA\n", "\ufeffA"),
])
def test_exact_text_normalization(raw, expected):
    assert core.hash_element(raw, core.TEXT_PROFILE)["hash"] == hashlib.sha256(expected.encode("utf-8")).hexdigest()


@pytest.mark.parametrize("value", [None, b"text", 0, True, "\ud800", "\udfff"])
def test_invalid_text_rejected(value):
    with pytest.raises(core.CoreValidationError):
        core.hash_element(value, core.TEXT_PROFILE)


def test_unicode_version_pinned_but_bytes_and_hash_receipts_independent(monkeypatch):
    certificate = receipt()
    monkeypatch.setattr(core.unicodedata, "unidata_version", "16.0.0")
    with pytest.raises(core.CoreValidationError) as exc:
        core.hash_element("hello", core.TEXT_PROFILE)
    assert exc.value.code == "UNSUPPORTED_UNICODE_VERSION"
    assert core.hash_element(b"", core.BYTES_PROFILE)["hash"] == hashlib.sha256(b"").hexdigest()
    assert check(certificate)["status"] == "VERIFIED_RECEIPT"


def test_bytes_are_exact_and_profiles_and_order_are_bound():
    assert core.hash_element(b"A \r\n", core.BYTES_PROFILE)["hash"] != core.hash_element("A \r\n", core.TEXT_PROFILE)["hash"]
    with pytest.raises(core.CoreValidationError):
        core.hash_element("A", core.BYTES_PROFILE)
    with pytest.raises(core.CoreValidationError):
        core.hash_element(bytearray(b"A"), core.BYTES_PROFILE)
    first = core.make_pair("A", "B")
    assert core.derive_pair_id(first) != core.derive_pair_id(core.make_pair("B", "A"))
    other_profile = deepcopy(first)
    other_profile["par1"]["profile"] = core.BYTES_PROFILE
    assert core.derive_pair_id(first) != core.derive_pair_id(other_profile)


def test_canonical_order_and_domain_separation():
    assert core.canonical_bytes({"z": "slash/", "a": {"b": "x"}}) == b'{"a":{"b":"x"},"z":"slash/"}'
    assert core.canonical_bytes({"z": "\n\t\"\\", "a": ""}) == b'{"a":"","z":"\\n\\t\\\"\\\\"}'
    assert core.derive_pair_id(pair()) != hashlib.sha256(core.canonical_bytes(pair())).hexdigest()


@pytest.mark.parametrize("bad", [None, [], {"a": None}, {"a": 1}, {"a": True}, {"a": 1.1}, {"a": []}, {"a": "\u00e9"}, {1: "x"}])
def test_canonical_rejects_other_value_vocabulary(bad):
    with pytest.raises(core.CoreValidationError):
        core.canonical_bytes(bad)


@pytest.mark.parametrize("bad", [b'\xff', '{"a":"x","a":"y"}', '{"a":{"b":"x","b":"y"}}', '{"a":NaN}', '[]', 'null', '{', b'\xef\xbb\xbf{}'])
def test_json_rejects_duplicates_bad_utf8_nonobjects_and_constants(bad):
    with pytest.raises(core.CoreValidationError):
        core.strict_json_loads(bad)


def test_validate_pair_exact_schema():
    assert core.validate_pair(pair()) is not None
    for transform in (
        lambda p: p.update(extra="x"),
        lambda p: p["par1"].update(extra="x"),
        lambda p: p["par1"].update(hash="A" * 64),
        lambda p: p["par1"].update(hash="a" * 63),
        lambda p: p["par1"].update(profile="future"),
        lambda p: p.update(par2=None),
    ):
        value = pair()
        transform(value)
        with pytest.raises(core.CoreValidationError):
            core.validate_pair(value)


def test_signer_snapshots_caller_pair():
    supplied = pair()
    certificate = core.sign_receipt(supplied, signing_key(), issuer_id=ISSUER, environment="LAB", receipt_id=RECEIPT_ID, received_at=RECEIVED_AT)
    supplied["par1"]["hash"] = "0" * 64
    assert check(certificate)["status"] == "VERIFIED_RECEIPT"


@pytest.mark.parametrize(("field", "value"), [
    ("protocol_version", "future"), ("hash_algorithm", "sha512"),
    ("signature_algorithm", "rsa"), ("issuer_id", "another:issuer"),
    ("key_id", "0" * 64), ("environment", "STAGING"),
    ("receipt_id", "223e4567-e89b-42d3-a456-426614174000"),
    ("received_at", "2026-10-10T12:00:01.000000Z"), ("evidence", "SOURCE_OBSERVED"),
    ("pair_id", "0" * 64),
])
def test_every_signed_body_field_tamper_detected(field, value):
    certificate = receipt()
    certificate["body"][field] = value
    # Explicit candidate permits signature verification even when issuer tuple changes.
    outcome = check(certificate, candidate_keys={core.key_id(signing_key().public_key()): signing_key().public_key()})
    assert outcome["status"] not in ("VERIFIED_RECEIPT", "VERIFIED_CONTENT")
    assert outcome["schema"] == "FAIL" or outcome["signature"] != "PASS"


def test_pair_change_and_rebinding_still_break_signature():
    certificate = receipt()
    certificate["body"]["pair"]["par1"]["hash"] = "0" * 64
    assert check(certificate)["signature"] == "FAIL"
    assert check(certificate)["pair_binding"] == "FAIL"
    certificate["body"]["pair_id"] = core.derive_pair_id(certificate["body"]["pair"])
    assert check(certificate)["pair_binding"] == "PASS"
    assert check(certificate)["signature"] == "FAIL"


def test_signed_inconsistent_binding_rejected_independently():
    certificate = receipt()
    certificate["body"]["pair_id"] = "0" * 64
    certificate["signature"] = signing_key().sign(core.CERTIFICATE_DOMAIN + core.canonical_bytes(certificate["body"])).hex()
    outcome = check(certificate)
    assert outcome["signature"] == "PASS"
    assert outcome["status"] == "INVALID_PAIR_BINDING"


def test_signature_mutation_wrong_key_and_missing_key():
    certificate = receipt()
    certificate["signature"] = "00" * 64
    assert check(certificate)["status"] == "INVALID_SIGNATURE"
    unknown = check(trusted_keys={})
    assert unknown["status"] == "KEY_UNAVAILABLE" and unknown["signature"] == "NOT_CHECKED"
    wrong = Ed25519PrivateKey.from_private_bytes(bytes(range(32))).public_key()
    wrong_outcome = check(trusted_keys={}, candidate_keys={core.key_id(signing_key().public_key()): wrong})
    assert wrong_outcome["status"] == "INVALID_SIGNATURE"
    assert wrong_outcome["signature"] == "FAIL"


def test_unknown_candidate_revocation_and_environment_are_independent():
    public_key = signing_key().public_key()
    unknown = check(trusted_keys={}, candidate_keys={core.key_id(public_key): public_key})
    assert unknown["signature"] == "PASS" and unknown["status"] == "UNTRUSTED_ISSUER"
    revoked = check(revoked_keys={core.key_id(public_key)})
    assert revoked["signature"] == "PASS" and revoked["issuer_trust"] == "REVOKED"
    assert revoked["status"] == "KEY_REVOKED"
    assert check(expected_environment="PRODUCTION")["status"] == "ENVIRONMENT_MISMATCH"


def test_content_absent_partial_pass_and_mismatch_never_promoted():
    absent = check()
    assert absent["content"] == "NOT_CHECKED" and absent["status"] == "VERIFIED_RECEIPT"
    partial = check(originals={"par1": ORIGINALS["par1"]})
    assert partial["content_checks"]["par1"] == "PASS"
    assert partial["content"] == "NOT_CHECKED" and partial["status"] == "VERIFIED_RECEIPT"
    assert check(originals=ORIGINALS)["status"] == "VERIFIED_CONTENT"
    wrong = check(originals={"par1": {"text": "different"}})
    assert wrong["signature"] == "PASS" and wrong["content"] == "FAIL"
    assert wrong["status"] == "CONTENT_MISMATCH"


@pytest.mark.parametrize("originals", [
    [], {"par3": {"text": "x"}}, {"par1": None}, {"par1": {"base64": "QQ=="}},
    {"par2": {"text": "x"}}, {"par1": {"text": "x", "extra": "x"}},
    {"par1": {"text": None}}, {"par1": {"text": "\ud800"}},
    {"par2": {"base64": "AP8K\n"}}, {"par2": {"base64": "AA"}},
    {"par2": {"base64": "AP8K="}}, {"par2": {"base64": "_w=="}},
    {"par2": {"base64": "AB=="}},
])
def test_originals_validate_before_trust_or_crypto(originals):
    with pytest.raises(core.CoreValidationError) as exc:
        core.verify_receipt(receipt(), trusted_keys=object(), expected_environment="LAB", originals=originals)
    assert exc.value.code == "MALFORMED_ORIGINALS"


@pytest.mark.parametrize(("field", "value"), [
    ("received_at", "2026-02-30T12:00:00.000000Z"),
    ("received_at", "2026-10-10T12:00:00Z"),
    ("received_at", "2026-10-10T12:00:00.000000+00:00"),
    ("receipt_id", RECEIPT_ID.upper()),
    ("receipt_id", "123e4567-e89b-12d3-a456-426614174000"),
    ("issuer_id", "a|b"), ("issuer_id", "\u00e9"), ("environment", "lab"),
    ("key_id", True), ("pair", []),
])
def test_bad_schema_rejected_before_trust_lookup(field, value):
    certificate = receipt()
    certificate["body"][field] = value
    result = core.verify_receipt(certificate, trusted_keys=object(), expected_environment="LAB")
    assert result["status"] == "MALFORMED_CERTIFICATE" and result["signature"] == "NOT_CHECKED"


def test_envelope_extras_and_unknown_version_fail_closed():
    certificate = receipt()
    certificate["issuer_pk_url"] = "http://arbitrary.invalid/key"
    assert check(certificate)["schema"] == "FAIL"
    certificate = receipt()
    certificate["body"]["protocol_version"] = "IAHASH-FUTURE"
    assert check(certificate)["status"] == "UNSUPPORTED_VERSION"
    certificate = receipt()
    certificate["body"]["pair"]["protocol_version"] = "IAHASH-FUTURE"
    assert check(certificate)["status"] == "UNSUPPORTED_VERSION"


def test_all_independent_failures_returned_in_summary_priority():
    certificate = receipt()
    certificate["body"]["pair_id"] = "0" * 64
    result = check(certificate, expected_environment="PRODUCTION", originals={"par1": {"text": "wrong"}}, revoked_keys={core.key_id(signing_key().public_key())})
    assert result["status"] == "INVALID_SIGNATURE"
    assert result["errors"] == ["INVALID_SIGNATURE", "KEY_REVOKED", "ENVIRONMENT_MISMATCH", "INVALID_PAIR_BINDING", "CONTENT_MISMATCH"]


def legacy_document():
    # Independently published historical vector; signature is not generated here.
    return {
        "protocol_version": "IAHASH-1.2", "prompt_id": None,
        "h_prompt": "559aead08264d5795d3909718cdd05abd49572e84fe55590eef31a88a08fdffd",
        "h_response": "df7e70e5021544f4834bbee64a9e3789febc4be81470df629cad6ddb03320a5c",
        "model": "gpt-x|extra", "timestamp": "2026-10-10T12:00:00Z",
        "h_total": "f12049a1b68ef4b46040384f1c2e877796f35cc865cc85b33e476aea9a073a00",
        "signature": "5eb0ee8f418fe0c577c7119a55d93766d2b0deea584c431843192c347f2eefdf7419629f4eb5646cfb547fb4119702e6bc9d0ed435f65143f7aecc2be8506805",
        "iah_id": "644tCxbwWfCLxt25",
        "issuer_id": "unsigned-claim", "issuer_pk_url": "http://never-fetched.invalid/key",
    }


def test_explicit_legacy_reader_preserves_known_bytes_and_limits():
    document = legacy_document()
    result = core.verify_legacy_v1_2(document, signing_key().public_key())
    assert result["status"] == "LEGACY_LIMITED"
    assert result["signature"] == result["pair_binding"] == result["identifier"] == "PASS"
    assert result["content"] == "NOT_CHECKED" and result["issuer_trust"] == "UNKNOWN"
    assert "DELIMITER_AMBIGUITY" in result["limitations"]
    with_originals = core.verify_legacy_v1_2(document, signing_key().public_key(), prompt_text="A", response_text="B")
    assert with_originals["content"] == "PASS" and with_originals["status"] == "LEGACY_LIMITED"
    document.update(model="gpt-x", timestamp="extra|2026-10-10T12:00:00Z", issuer_id="different-unsigned-claim")
    assert core.verify_legacy_v1_2(document, signing_key().public_key())["signature"] == "PASS"


def test_legacy_wrong_key_tamper_original_and_id_are_distinct():
    public_key = signing_key().public_key()
    wrong_key = Ed25519PrivateKey.from_private_bytes(bytes(range(32))).public_key()
    assert core.verify_legacy_v1_2(legacy_document(), wrong_key)["signature"] == "FAIL"
    assert core.verify_legacy_v1_2(legacy_document(), public_key, prompt_text="wrong")["content"] == "FAIL"
    document = legacy_document()
    document["iah_id"] = "arbitrary"
    outcome = core.verify_legacy_v1_2(document, public_key)
    assert outcome["signature"] == "PASS" and outcome["identifier"] == "FAIL"
    document["model"] = "tampered"
    outcome = core.verify_legacy_v1_2(document, public_key)
    assert outcome["signature"] == "PASS" and outcome["pair_binding"] == "FAIL"


def test_legacy_reader_never_guesses_another_format():
    document = legacy_document()
    document["protocol_version"] = "IAHASH-1"
    assert core.verify_legacy_v1_2(document, signing_key().public_key())["status"] == "UNSUPPORTED_VERSION"
    assert check(legacy_document())["status"] == "MALFORMED_CERTIFICATE"


def test_core_import_and_operations_without_legacy_network_storage(tmp_path):
    project = Path(__file__).resolve().parents[1]
    deps = project.parent / "iahash-test-deps"
    code = f'''
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, {str(deps)!r})
sys.path.insert(0, {str(project)!r})
class Guard:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {{'iahash','iahash_server','sqlite3','httpx','urllib','socket'}}:
            raise AssertionError('Forbidden Core dependency: ' + fullname)
sys.meta_path.insert(0, Guard())
import iahash_core as c
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
k=Ed25519PrivateKey.from_private_bytes(bytes(range(32)))
p=c.make_pair('A','B')
r=c.sign_receipt(p,k,issuer_id='test',environment='LAB',receipt_id={RECEIPT_ID!r},received_at={RECEIVED_AT!r})
assert c.verify_receipt(r,trusted_keys={{('test','LAB',c.key_id(k.public_key())):k.public_key()}},expected_environment='LAB')['status']=='VERIFIED_RECEIPT'
'''
    completed = subprocess.run([sys.executable, "-c", code], cwd=tmp_path, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr
    assert list(tmp_path.iterdir()) == []
