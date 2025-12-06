"""Cryptographic primitives for IA-HASH v1.2.

Responsibilities:
- Text normalisation according to PROTOCOL_1.2.
- SHA256 hashing helpers.
- Ed25519 signing and verification.
- Base58 encoding used for iah_id generation.
"""

from __future__ import annotations

import base64
import hashlib
import unicodedata
from pathlib import Path
from typing import Optional

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

KEY_DIR = Path("/data/keys")
PRIVATE_KEY_NAME = "issuer_ed25519.private"
PUBLIC_KEY_NAME = "issuer_ed25519.pub"

# Bitcoin base58 alphabet
BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def normalize_text(text: str) -> bytes:
    """Normalize text according to IA-HASH v1.2 rules.

    Steps:
    - Unicode NFC cleanup
    - Replace CRLF/CR with LF
    - Trim trailing whitespace on each line
    - Remove trailing blank lines
    - Encode as UTF-8 bytes
    """

    if text is None:
        text = ""
    normalized = unicodedata.normalize("NFC", text)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in normalized.split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    normalized = "\n".join(lines)
    return normalized.encode("utf-8")


def sha256_hex(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def encode_base58(data: bytes) -> str:
    """Encode bytes into a base58 string without external deps."""

    if not data:
        return ""
    num = int.from_bytes(data, "big")
    encoded = ""
    while num > 0:
        num, rem = divmod(num, 58)
        encoded = BASE58_ALPHABET[rem] + encoded
    # handle leading zeros
    padding = 0
    for b in data:
        if b == 0:
            padding += 1
        else:
            break
    return (BASE58_ALPHABET[0] * padding) + encoded


def load_private_key(path: Optional[Path] = None) -> Ed25519PrivateKey:
    key_path = path or KEY_DIR / PRIVATE_KEY_NAME
    data = key_path.read_bytes()
    return serialization.load_pem_private_key(data, password=None)


def load_public_key(path: Optional[Path] = None) -> Ed25519PublicKey:
    key_path = path or KEY_DIR / PUBLIC_KEY_NAME
    data = key_path.read_bytes()
    return serialization.load_pem_public_key(data)


def sign_message(message: bytes, key_path: Optional[Path] = None) -> str:
    private_key = load_private_key(key_path)
    signature = private_key.sign(message)
    return base64.b64encode(signature).decode("ascii")


def verify_signature(message: bytes, signature_b64: str, public_key: Ed25519PublicKey) -> bool:
    try:
        public_key.verify(base64.b64decode(signature_b64), message)
        return True
    except Exception:
        return False


def derive_iah_id(h_total: str) -> str:
    digest = hashlib.sha256(h_total.encode("utf-8")).digest()
    return encode_base58(digest)[:16]
