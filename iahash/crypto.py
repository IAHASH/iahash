# iahash/crypto.py
"""
Core cryptographic primitives for IA-HASH v1.2.

Implementa:

- Normalización de texto (protocolo 1.2)
- Helpers SHA-256
- Firmas / verificación Ed25519
- Cálculo de hashes para pares (prompt + respuesta)
- IA-HASH ID público (`iah_id`, base58)
- Funciones de compatibilidad con versiones anteriores:
  - normalise(...)
  - sign_message(...)
  - verify_signature(...)
  - derive_iah_id(...)

Las claves del emisor se gestionan vía ficheros PEM, generados por `start.sh`:

    /data/keys/issuer_ed25519.private
    /data/keys/issuer_ed25519.pub
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
# Constantes y paths de claves
# ============================================================================

PROTOCOL_VERSION = "IAHASH-1.2"


def get_key_dir() -> Path:
    key_dir_env = os.getenv("IAHASH_KEY_DIR") or os.getenv("IAHASH_KEYS_DIR")
    return Path(key_dir_env) if key_dir_env else Path("/data/keys")


def get_default_private_key_path() -> Path:
    override = os.getenv("IAHASH_PRIVATE_KEY_FILE")
    if override:
        return Path(override)
    return get_key_dir() / "issuer_ed25519.private"


def get_default_public_key_path() -> Path:
    override = os.getenv("IAHASH_PUBLIC_KEY_FILE")
    if override:
        return Path(override)
    return get_key_dir() / "issuer_ed25519.pub"


# Directorio y paths por defecto (alineados con start.sh)
KEY_DIR = get_key_dir()
DEFAULT_PRIVATE_KEY_PATH = get_default_private_key_path()
DEFAULT_PUBLIC_KEY_PATH = get_default_public_key_path()


# ============================================================================
# Normalización de texto
# ============================================================================

def normalize_text(text: str | None) -> str:
    """
    Normaliza texto según IA-HASH v1.2:

    - None -> ""
    - Unicode NFC
    - CRLF / CR -> LF
    - Quita espacios/tabs al final de cada línea
    - Elimina líneas vacías finales
    - Mantiene saltos de línea internos

    Devuelve str normalizado (UTF-8 se aplica en otra función).
    """
    if text is None:
        text = ""

    # Unicode NFC
    text = unicodedata.normalize("NFC", text)

    # Normalizar finales de línea a "\n"
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Strip de espacios/tabs al final de cada línea
    lines = [line.rstrip(" \t") for line in text.split("\n")]

    # Eliminar líneas vacías al final
    while lines and lines[-1] == "":
        lines.pop()

    return "\n".join(lines)


def normalized_bytes(text: str | None) -> bytes:
    """Atajo: normaliza y luego codifica a bytes UTF-8."""
    return normalize_text(text).encode("utf-8")


# Función de compatibilidad usada en tests antiguos
def normalise(text: str | None) -> bytes:
    """
    Compatibilidad con versiones anteriores.

    Antes la función principal se llamaba `normalise` y devolvía bytes.
    Ahora la implementación real está en `normalize_text` + `normalized_bytes`,
    pero mantenemos este wrapper para no romper código/test antiguos.
    """
    return normalized_bytes(text)


# ============================================================================
# Helpers SHA-256
# ============================================================================

def sha256_hex(data: bytes) -> str:
    """Devuelve SHA-256 en minúsculas, formato hex."""
    return hashlib.sha256(data).hexdigest()


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
    """
    Calcula h_prompt, h_response y h_total para un par prompt–respuesta.

    Definido en PROTOCOL 1.2:

        h_prompt   = SHA256(normalised_prompt)
        h_response = SHA256(normalised_response)
        h_total    = SHA256(
                        protocol_version | prompt_id | h_prompt |
                        h_response | model | timestamp
                     )

    Donde '|' es el pipe literal, y prompt_id vacío se representa como "".
    """
    # 1) Normalizar y hashear prompt / respuesta
    h_prompt = sha256_hex(normalized_bytes(prompt_text))
    h_response = sha256_hex(normalized_bytes(response_text))

    # 2) Construir string combinado
    pid_component = prompt_id or ""  # null → ""
    combined_str = "|".join(
        [
            protocol_version,
            pid_component,
            h_prompt,
            h_response,
            model,
            timestamp,
        ]
    )
    h_total = sha256_hex(combined_str.encode("utf-8"))

    return PairHashes(h_prompt=h_prompt, h_response=h_response, h_total=h_total)


# ============================================================================
# Gestión de claves Ed25519
# ============================================================================

def load_ed25519_private_key(path: Path) -> ed25519.Ed25519PrivateKey:
    """
    Carga una clave privada Ed25519 desde PEM (sin password).
    """
    data = path.read_bytes()
    return serialization.load_pem_private_key(data, password=None)


def load_ed25519_public_key(path: Path) -> ed25519.Ed25519PublicKey:
    """Carga una clave pública Ed25519 desde PEM."""
    data = path.read_bytes()
    return serialization.load_pem_public_key(data)


def generate_ed25519_keypair() -> Tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey]:
    """
    Genera un nuevo par de claves Ed25519 en memoria.

    La persistencia en disco se deja al caller (p. ej. start.sh).
    """
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    return private_key, public_key


def save_ed25519_private_key(key: ed25519.Ed25519PrivateKey, path: Path) -> None:
    """Guarda una clave privada Ed25519 en PEM (sin password)."""
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    path.write_bytes(pem)


def save_ed25519_public_key(key: ed25519.Ed25519PublicKey, path: Path) -> None:
    """Guarda una clave pública Ed25519 en PEM."""
    pem = key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    path.write_bytes(pem)


def load_issuer_private_key(path: Path | None = None) -> ed25519.Ed25519PrivateKey:
    """
    Carga la clave privada del emisor desde disco usando el path por defecto
    (o uno explícito si se indica).
    """
    key_path = path or get_default_private_key_path()
    return load_ed25519_private_key(key_path)


def load_issuer_public_key(path: Path | None = None) -> ed25519.Ed25519PublicKey:
    """Carga la clave pública del emisor."""
    key_path = path or get_default_public_key_path()
    return load_ed25519_public_key(key_path)


# ============================================================================
# Firmas (nivel bajo y nivel protocolo)
# ============================================================================

def sign_message(message: bytes, key_path: Path | None = None) -> str:
    """
    Firma un mensaje arbitrario con la clave privada del emisor y devuelve la
    firma en hex.

    Este helper es el que usan versiones anteriores de `issuer.py`.
    """
    private_key = load_issuer_private_key(key_path)
    signature = private_key.sign(message)
    return signature.hex()


def verify_signature(
    message: bytes,
    signature_hex: str,
    public_key: ed25519.Ed25519PublicKey,
) -> bool:
    """
    Verifica una firma Ed25519 sobre `message` con una clave pública dada.

    Devuelve True si la firma es válida, False en caso contrario.
    """
    try:
        signature = bytes.fromhex(signature_hex)
    except ValueError:
        return False

    try:
        public_key.verify(signature, message)
        return True
    except Exception:
        return False


def sign_h_total(
    private_key: ed25519.Ed25519PrivateKey,
    h_total_hex: str,
) -> str:
    """
    Firma h_total (hex) con Ed25519 y devuelve la firma en hex.

    Implementado encima de `sign_message` para mantener compatibilidad.
    """
    message = bytes.fromhex(h_total_hex)
    signature = private_key.sign(message)
    return signature.hex()


def verify_h_total_signature(
    public_key: ed25519.Ed25519PublicKey,
    h_total_hex: str,
    signature_hex: str,
) -> bool:
    """
    Verifica una firma sobre h_total (hex). Devuelve True si es válida.
    """
    message = bytes.fromhex(h_total_hex)
    return verify_signature(message, signature_hex, public_key)


# ============================================================================
# IA-HASH ID (iah_id) – Base58
# ============================================================================

_BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def _bytes_to_base58(data: bytes) -> str:
    """
    Encode bytes a base58 (alfabeto Bitcoin) sin dependencias externas.
    """
    num = int.from_bytes(data, byteorder="big")

    # Caso especial: todo ceros
    if num == 0:
        return _BASE58_ALPHABET[0]

    result_chars: list[str] = []
    while num > 0:
        num, rem = divmod(num, 58)
        result_chars.append(_BASE58_ALPHABET[rem])

    # Zeros iniciales -> '1'
    n_leading_zeros = len(data) - len(data.lstrip(b"\x00"))
    result_chars.extend(_BASE58_ALPHABET[0] for _ in range(n_leading_zeros))

    # Construido al revés
    return "".join(reversed(result_chars))


def compute_iah_id_from_h_total(h_total_hex: str) -> str:
    """
    Calcula el identificador público IA-HASH (iah_id) a partir de h_total:

        iah_id = base58(SHA256(h_total_bytes))[:16]

    donde h_total_bytes es la codificación UTF-8 de la representación hex de
    h_total.
    """
    h_bytes = h_total_hex.encode("utf-8")
    digest = hashlib.sha256(h_bytes).digest()
    b58 = _bytes_to_base58(digest)
    return b58[:16]


# Compatibilidad con código antiguo que llamaba `derive_iah_id`
def derive_iah_id(h_total_hex: str) -> str:
    """
    Alias de compatibilidad: antes la función se llamaba `derive_iah_id`.
    """
    return compute_iah_id_from_h_total(h_total_hex)
