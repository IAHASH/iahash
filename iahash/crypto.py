# iahash/crypto.py
"""Primitivas criptográficas para el protocolo IA-HASH v1.2.

Este módulo centraliza las operaciones de normalización de texto, hashing,
codificación base58 y gestión de claves/firmas Ed25519 usadas por la emisión y
verificación de documentos IA-HASH.
"""

from __future__ import annotations

import hashlib
import os
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519


# ============================================================================
# Constantes y rutas de claves
# ============================================================================

PROTOCOL_VERSION = "IAHASH-1.2"


def get_key_dir() -> Path:
    """Devuelve el directorio de claves, usando `/data/keys` por defecto."""

    key_dir_env = os.getenv("IAHASH_KEY_DIR") or os.getenv("IAHASH_KEYS_DIR")
    return Path(key_dir_env) if key_dir_env else Path("/data/keys")


def get_default_private_key_path() -> Path:
    """Ruta de la clave privada del emisor, respetando overrides por entorno."""

    override = os.getenv("IAHASH_PRIVATE_KEY_FILE")
    if override:
        return Path(override)
    return get_key_dir() / "issuer_ed25519.private"


def get_default_public_key_path() -> Path:
    """Ruta de la clave pública del emisor, respetando overrides por entorno."""

    override = os.getenv("IAHASH_PUBLIC_KEY_FILE")
    if override:
        return Path(override)
    return get_key_dir() / "issuer_ed25519.pub"


# ============================================================================
# Normalización de texto
# ============================================================================

def normalize_text(text: Optional[str]) -> str:
    """Normaliza texto según IA‑HASH v1.2.

    Pasos aplicados:
    1. ``None`` se trata como cadena vacía.
    2. Se aplica normalización Unicode NFC.
    3. Se unifican saltos de línea ``CRLF``/``CR`` a ``"\n"``.
    4. Se eliminan espacios en blanco al final de cada línea.
    5. Se descartan líneas vacías finales.
    """

    normalized = text or ""
    normalized = unicodedata.normalize("NFC", normalized)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip(" \t") for line in normalized.split("\n")]

    while lines and lines[-1] == "":
        lines.pop()

    return "\n".join(lines)


def normalized_bytes(text: Optional[str]) -> bytes:
    """Normaliza un texto y lo codifica en UTF-8."""

    return normalize_text(text).encode("utf-8")


# Función de compatibilidad usada en tests antiguos
def normalise(text: Optional[str]) -> bytes:
    """Alias de compatibilidad para código heredado que espera bytes."""

    return normalized_bytes(text)


# ============================================================================
# Helpers SHA-256
# ============================================================================

def sha256_hex(data: bytes) -> str:
    """Calcula SHA-256 y devuelve el digest en minúsculas, formato hex."""

    return hashlib.sha256(data).hexdigest()


# ============================================================================
# Base58
# ============================================================================

BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def base58_encode(data: bytes) -> str:
    """Codifica ``data`` en Base58 (alfabeto Bitcoin)."""

    num = int.from_bytes(data, "big")

    if num == 0:
        return BASE58_ALPHABET[0]

    encoded: list[str] = []
    while num > 0:
        num, remainder = divmod(num, 58)
        encoded.append(BASE58_ALPHABET[remainder])

    leading_zeroes = len(data) - len(data.lstrip(b"\x00"))
    encoded.extend(BASE58_ALPHABET[0] for _ in range(leading_zeroes))

    return "".join(reversed(encoded))


# ============================================================================
# Hashes de par (prompt + respuesta)
# ============================================================================

@dataclass
class PairHashes:
    """Hashes para un par prompt–respuesta bajo IA-HASH v1.2."""

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
    """Calcula ``h_prompt``, ``h_response`` y ``h_total`` para IA‑HASH 1.2.

    - ``h_prompt``   = SHA256(prompt normalizado)
    - ``h_response`` = SHA256(respuesta normalizada)
    - ``h_total``    = SHA256(protocol_version|prompt_id|h_prompt|h_response|model|timestamp)
    """

    h_prompt = sha256_hex(normalized_bytes(prompt_text))
    h_response = sha256_hex(normalized_bytes(response_text))

    prompt_component = prompt_id or ""
    combined = "|".join(
        [protocol_version, prompt_component, h_prompt, h_response, model, timestamp]
    )
    h_total = sha256_hex(combined.encode("utf-8"))

    return PairHashes(h_prompt=h_prompt, h_response=h_response, h_total=h_total)


# ============================================================================
# Gestión de claves Ed25519
# ============================================================================

def generate_ed25519_keypair() -> Tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey]:
    """Genera y devuelve un par de claves Ed25519."""

    private_key = ed25519.Ed25519PrivateKey.generate()
    return private_key, private_key.public_key()


def _ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def save_ed25519_private_key(
    key: ed25519.Ed25519PrivateKey, path: Optional[Path] = None
) -> Path:
    """Guarda una clave privada en PEM sin contraseña y devuelve la ruta."""

    path = path or get_default_private_key_path()
    _ensure_parent_dir(path)
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    path.write_bytes(pem)
    return path


def save_ed25519_public_key(
    key: ed25519.Ed25519PublicKey, path: Optional[Path] = None
) -> Path:
    """Guarda una clave pública en PEM y devuelve la ruta."""

    path = path or get_default_public_key_path()
    _ensure_parent_dir(path)
    pem = key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    path.write_bytes(pem)
    return path


def load_ed25519_private_key(path: Optional[Path] = None) -> ed25519.Ed25519PrivateKey:
    """Carga una clave privada Ed25519 (PEM sin contraseña)."""

    key_path = path or get_default_private_key_path()
    data = key_path.read_bytes()
    return serialization.load_pem_private_key(data, password=None)


def load_ed25519_public_key(path: Optional[Path] = None) -> ed25519.Ed25519PublicKey:
    """Carga una clave pública Ed25519 en formato PEM."""

    key_path = path or get_default_public_key_path()
    data = key_path.read_bytes()
    return serialization.load_pem_public_key(data)


def get_issuer_public_key_pem() -> bytes:
    """Obtiene la clave pública del emisor en formato PEM.

    Si el fichero de clave pública existe, se devuelve tal cual. Si solo está
    presente la clave privada, se deriva la pública, se guarda y se devuelve
    en memoria.
    """

    public_key_path = get_default_public_key_path()
    if public_key_path.exists():
        return public_key_path.read_bytes()

    private_key = load_ed25519_private_key()
    derived_public = private_key.public_key()
    pem = derived_public.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    save_ed25519_public_key(derived_public, public_key_path)
    return pem


# ============================================================================
# Firmas (nivel bajo y nivel protocolo)
# ============================================================================

def sign_message(message: bytes, private_key: ed25519.Ed25519PrivateKey) -> bytes:
    """Firma un mensaje arbitrario con Ed25519 y devuelve la firma en bytes."""

    return private_key.sign(message)


def verify_signature(
    message: bytes, signature: bytes, public_key: ed25519.Ed25519PublicKey
) -> bool:
    """Verifica una firma Ed25519. Devuelve ``True`` si es válida."""

    try:
        public_key.verify(signature, message)
        return True
    except Exception:
        return False


# ============================================================================
# IA-HASH ID (iah_id) – Base58
# ============================================================================

def derive_iah_id(h_total_hex: str) -> str:
    """Deriva el identificador público base58 a partir de ``h_total`` hex."""

    digest = hashlib.sha256(h_total_hex.encode("utf-8")).digest()
    return base58_encode(digest)[:16]
