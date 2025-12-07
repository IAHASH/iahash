# iahash/crypto.py
"""
Core cryptographic primitives for IA-HASH v1.2.

Implements:
- Text normalisation (protocol 1.2)
- SHA-256 hashing helpers
- Ed25519 signing / verification
- IA-HASH combined hash (h_total)
- IA-HASH public identifier (iah_id)

Protocol reference:
  - PROTOCOL_1.2.md
"""

from __future__ import annotations

import hashlib
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization


# -------- Normalisation -----------------------------------------------------


def normalize_text(text: str) -> str:
    """
    Normalise text according to IA-HASH v1.2 rules:

    - Unicode NFC
    - CRLF / CR -> LF
    - Trim trailing spaces on each line
    - Remove trailing empty lines
    - Keep internal newlines intact

    Returns a normalised string. Later we encode as UTF-8 bytes.
    """
    if text is None:
        text = ""

    # Unicode NFC
    text = unicodedata.normalize("NFC", text)

    # Normalise line endings to "\n"
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Strip trailing spaces on each line
    lines = [line.rstrip(" \t") for line in text.split("\n")]

    # Remove trailing empty lines
    while lines and lines[-1] == "":
        lines.pop()

    return "\n".join(lines)


def normalized_bytes(text: str) -> bytes:
    """
    Convenience: normalise and then encode to UTF-8 bytes.
    """
    return normalize_text(text).encode("utf-8")


# -------- Hash helpers ------------------------------------------------------


def sha256_hex(data: bytes) -> str:
    """Return SHA-256 as lowercase hex string."""
    return hashlib.sha256(data).hexdigest()


@dataclass
class PairHashes:
    """Hashes for a prompt–response pair under IA-HASH v1.2."""

    h_prompt: str
    h_response: str
    h_total: str


def compute_pair_hashes(
    prompt_text: str,
    response_text: str,
    *,
    protocol_version: str,
    prompt_id: Optional[str],
    model: str,
    timestamp: str,
) -> PairHashes:
    """
    Compute h_prompt, h_response and h_total for a prompt–response pair.

    According to PROTOCOL_1.2:

      h_prompt   = SHA256(normalised_prompt)
      h_response = SHA256(normalised_response)
      h_total    = SHA256(
                      protocol_version | prompt_id | h_prompt |
                      h_response | model | timestamp
                    )

    Where '|' is literal pipe and empty string is used for null prompt_id.
    """

    # 1) Normalise both texts and hash individually
    h_prompt = sha256_hex(normalized_bytes(prompt_text))
    h_response = sha256_hex(normalized_bytes(response_text))

    # 2) Build combined string
    pid_component = prompt_id or ""  # null → empty string
    combined = "|".join(
        [
            protocol_version,
            pid_component,
            h_prompt,
            h_response,
            model,
            timestamp,
        ]
    ).encode("utf-8")

    h_total = sha256_hex(combined)

    return PairHashes(h_prompt=h_prompt, h_response=h_response, h_total=h_total)


# -------- Ed25519 key handling ----------------------------------------------


def load_ed25519_private_key(path: Path) -> ed25519.Ed25519PrivateKey:
    """
    Load an Ed25519 private key from a PEM file.

    The key should be written without password, in the usual OpenSSL/cryptography format.
    """
    data = path.read_bytes()
    return serialization.load_pem_private_key(data, password=None)


def load_ed25519_public_key(path: Path) -> ed25519.Ed25519PublicKey:
    """
    Load an Ed25519 public key from a PEM file.
    """
    data = path.read_bytes()
    return serialization.load_pem_public_key(data)


def generate_ed25519_keypair() -> Tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey]:
    """
    Generate a new Ed25519 keypair (in-memory).
    Persisting is responsibility of the caller/startup script.
    """
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    return private_key, public_key


def save_ed25519_private_key(key: ed25519.Ed25519PrivateKey, path: Path) -> None:
    """
    Save an Ed25519 private key to PEM (no password).
    """
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    path.write_bytes(pem)


def save_ed25519_public_key(key: ed25519.Ed25519PublicKey, path: Path) -> None:
    """
    Save an Ed25519 public key to PEM.
    """
    pem = key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    path.write_bytes(pem)


# -------- Signing helpers ---------------------------------------------------


def sign_h_total(
    private_key: ed25519.Ed25519PrivateKey,
    h_total_hex: str,
) -> str:
    """
    Sign h_total (hex string) with Ed25519 and return signature as hex string.
    """
    # Interpret h_total as raw bytes of its hex representation (protocol choice).
    message = bytes.fromhex(h_total_hex)
    signature = private_key.sign(message)
    return signature.hex()


def verify_h_total_signature(
    public_key: ed25519.Ed25519PublicKey,
    h_total_hex: str,
    signature_hex: str,
) -> bool:
    """
    Verify an Ed25519 signature over h_total.

    Returns True if signature is valid, False otherwise.
    """
    message = bytes.fromhex(h_total_hex)
    signature = bytes.fromhex(signature_hex)
    try:
        public_key.verify(signature, message)
        return True
    except Exception:
        return False


# -------- IA-HASH ID (iah_id) -----------------------------------------------

_BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def _bytes_to_base58(data: bytes) -> str:
    """
    Encode bytes into a base58 string (Bitcoin alphabet).

    Implemented without external dependencies to keep the library lightweight.
    """
    # Convert bytes to integer
    num = int.from_bytes(data, byteorder="big")

    # Special case zero
    if num == 0:
        return _BASE58_ALPHABET[0]

    result_chars = []
    while num > 0:
        num, rem = divmod(num, 58)
        result_chars.append(_BASE58_ALPHABET[rem])

    # Deal with leading zeros: each leading 0x00 becomes a leading '1'
    n_leading_zeros = len(data) - len(data.lstrip(b"\x00"))
    result_chars.extend(_BASE58_ALPHABET[0] for _ in range(n_leading_zeros))

    # We built the string in reverse
    return "".join(reversed(result_chars))


def compute_iah_id_from_h_total(h_total_hex: str) -> str:
    """
    Compute the public IA-HASH identifier (iah_id) from h_total:

        iah_id = base58(SHA256(h_total_bytes))[:16]

    Where h_total_bytes is the UTF-8 encoding of the hex string representation.

    The 16-char prefix is enough for uniqueness and human use.
    """
    # Here we treat the hex string itself as bytes, not the underlying digest.
    h_bytes = h_total_hex.encode("utf-8")
    digest = hashlib.sha256(h_bytes).digest()
    b58 = _bytes_to_base58(digest)
    return b58[:16]
