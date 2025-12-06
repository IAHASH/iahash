from __future__ import annotations

from pathlib import Path
import hashlib
import re
import unicodedata

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


INVISIBLE_CHARS = [
    "\u200b",  # zero width space
    "\ufeff",  # zero width no-break space
    "\u200c",  # zero width non-joiner
    "\u200d",  # zero width joiner
    "\u2060",  # word joiner
]


def normalise(text: str) -> bytes:
    """Normalise text using the IHS-1 ruleset.

    Steps:
    - Unicode NFC normalisation
    - Replace CRLF/CR with LF
    - Remove zero-width characters and non-breaking spaces
    - Collapse internal whitespace to single spaces per line
    - Trim leading/trailing whitespace and empty lines
    - Encode as UTF-8 bytes
    """

    # Unicode normalisation
    normalised = unicodedata.normalize("NFC", text or "")

    # Standardise newlines
    normalised = normalised.replace("\r\n", "\n").replace("\r", "\n")

    # Remove invisibles and NBSP
    for ch in INVISIBLE_CHARS:
        normalised = normalised.replace(ch, "")
    normalised = normalised.replace("\xa0", " ")

    # Collapse whitespace per line
    lines = [re.sub(r"\s+", " ", line).strip() for line in normalised.split("\n")]
    # Remove leading/trailing empty lines after trimming
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()

    collapsed = "\n".join(lines)
    return collapsed.encode("utf-8")


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
