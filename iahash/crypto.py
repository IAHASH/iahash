from __future__ import annotations

from pathlib import Path
import hashlib

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


def normalise(text: str) -> bytes:
    """Normalise text before hashing.

    Steps:
    - Convert CRLF / CR to LF
    - Strip trailing spaces on each line
    - Encode as UTF-8
    """

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    text = text.rstrip("\n")
    return text.encode("utf-8")


def sha256_hex(data: bytes) -> str:
    """Return the SHA256 digest of ``data`` as a hex string."""

    return hashlib.sha256(data).hexdigest()


def load_private_key(path: str | Path) -> Ed25519PrivateKey:
    """Load an Ed25519 private key from PEM."""

    path = Path(path)
    with path.open("rb") as handle:
        return serialization.load_pem_private_key(handle.read(), password=None)


def load_public_key(path: str | Path) -> Ed25519PublicKey:
    """Load an Ed25519 public key from PEM."""

    path = Path(path)
    with path.open("rb") as handle:
        return serialization.load_pem_public_key(handle.read())


def sign_hex(h_total: str, sk: Ed25519PrivateKey) -> str:
    """Sign the UTF-8 encoded ``h_total`` and return the signature as hex."""

    signature = sk.sign(h_total.encode("utf-8"))
    return signature.hex()


def verify_signature_hex(h_total: str, sig_hex: str, pk: Ed25519PublicKey) -> bool:
    """Verify that ``sig_hex`` matches ``h_total`` for the provided public key."""

    try:
        pk.verify(bytes.fromhex(sig_hex), h_total.encode("utf-8"))
    except Exception:
        return False
    return True
