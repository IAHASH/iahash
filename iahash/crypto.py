import hashlib
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives import serialization


def normalise(text: str) -> bytes:
    """
    Normalise text before hashing:
    - Convert CRLF / CR to LF
    - Strip trailing spaces on each line
    - Encode as UTF-8
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    return text.encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_private_key(path: str | Path) -> Ed25519PrivateKey:
    path = Path(path)
    with path.open("rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)


def load_public_key(path: str | Path) -> Ed25519PublicKey:
    path = Path(path)
    with path.open("rb") as f:
        return serialization.load_pem_public_key(f.read())


def sign_hex(h_total: str, sk: Ed25519PrivateKey) -> str:
    """
    Sign the hex-encoded h_total and return signature as hex string.
    """
    sig = sk.sign(h_total.encode("utf-8"))
    return sig.hex()


def verify_signature_hex(h_total: str, sig_hex: str, pk: Ed25519PublicKey) -> bool:
    try:
        pk.verify(bytes.fromhex(sig_hex), h_total.encode("utf-8"))
        return True
    except Exception:
        return False
