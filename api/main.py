# api/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Any, Dict
from datetime import datetime, timezone
import hashlib
import json
import os

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

# ============================================================================
# Configuración básica
# ============================================================================

IAHASH_VERSION = "IA-HASH-1.0"
HASH_ALG = "sha256"

# Rutas donde guardamos las claves (persistentes entre reinicios)
SECRET_KEY_PATH = os.getenv("IAHASH_SECRET_KEY_FILE", "secret_ed25519.key")
PUBLIC_KEY_PATH = os.getenv("IAHASH_PUBLIC_KEY_FILE", "public_ed25519.key")


def _load_or_create_keys() -> tuple[Ed25519PrivateKey, Ed25519PublicKey]:
    """
    Carga o genera un par de claves Ed25519.

    - Si existen archivos, los lee.
    - Si no, genera claves nuevas y las guarda en disco.
    """
    if os.path.exists(SECRET_KEY_PATH) and os.path.exists(PUBLIC_KEY_PATH):
        # Cargar claves existentes
        with open(SECRET_KEY_PATH, "rb") as f:
            priv_bytes = f.read()
        private_key = serialization.load_pem_private_key(
            priv_bytes, password=None
        )
        with open(PUBLIC_KEY_PATH, "rb") as f:
            pub_bytes = f.read()
        public_key = serialization.load_pem_public_key(pub_bytes)
        return private_key, public_key

    # Generar claves nuevas
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    # Guardar en disco (PEM, sin password)
    priv_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    with open(SECRET_KEY_PATH, "wb") as f:
        f.write(priv_pem)
    with open(PUBLIC_KEY_PATH, "wb") as f:
        f.write(pub_pem)

    return private_key, public_key


PRIVATE_KEY, PUBLIC_KEY = _load_or_create_keys()


def _public_key_hex() -> str:
    """Devuelve la clave pública Ed25519 en hex string (32 bytes)."""
    raw = PUBLIC_KEY.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return raw.hex()


# ============================================================================
# Utilidades IA-HASH
# ============================================================================


def canonicalize_text(value: str | None) -> str:
    """
    Normaliza texto para IA-HASH:

    - None -> "".
    - Normaliza saltos de línea a '\n'.
    - Elimina espacios al final de cada línea.
    - Elimina líneas vacías al principio y al final.
    """
    if value is None:
        return ""

    # Normalizar saltos de línea
    value = value.replace("\r\n", "\n").replace("\r", "\n")

    lines = value.split("\n")
    # strip líneas vacías al principio
    while lines and lines[0].strip() == "":
        lines.pop(0)
    # strip líneas vacías al final
    while lines and lines[-1].strip() == "":
        lines.pop()

    # quitar espacios a la derecha en cada línea
    lines = [line.rstrip() for line in lines]

    return "\n".join(lines)


def canonical_payload(
    prompt: str,
    contexto: Optional[str],
    respuesta: str,
    metadata: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Construye el JSON canónico IA-HASH (sin hash/firma):

    {
        "prompt": ...,
        "contexto": ...,
        "respuesta": ...,
        "metadata": {...}
    }
    """
    return {
        "prompt": canonicalize_text(prompt),
        "contexto": canonicalize_text(contexto) if contexto is not None else None,
        "respuesta": canonicalize_text(respuesta),
        "metadata": metadata,
    }


def canonical_json_str(payload: Dict[str, Any]) -> str:
    """
    Serializa el payload IA-HASH de forma determinista:

    - sort_keys=True
    - separators sin espacios
    - ensure_ascii=False para respetar UTF-8
    """
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_hash(canonical_str: str) -> str:
    """Hash del JSON canónico con SHA256 (o el algoritmo que definas)."""
    h = hashlib.new(HASH_ALG)
    h.update(canonical_str.encode("utf-8"))
    return h.hexdigest()


def sign_canonical(canonical_str: str) -> str:
    """Firma Ed25519 del JSON canónico (hex)."""
    signature = PRIVATE_KEY.sign(canonical_str.encode("utf-8"))
    return signature.hex()


def verify_signature(public_key_hex: str, canonical_str: str, signature_hex: str) -> bool:
    """Verifica la firma Ed25519. Devuelve True si es válida."""
    try:
        pub_raw = bytes.fromhex(public_key_hex)
        public_key = Ed25519PublicKey.from_public_bytes(pub_raw)
        signature = bytes.fromhex(signature_hex)
        public_key.verify(signature, canonical_str.encode("utf-8"))
        return True
    except (ValueError, InvalidSignature):
        return False


# ============================================================================
# Modelos Pydantic (entrada/salida API)
# ============================================================================


class IssueRequest(BaseModel):
    prompt: str = Field(..., description="Prompt maestro o texto enviado a la IA.")
    response: str = Field(..., description="Respuesta completa del modelo.")
    model: Optional[str] = Field(None, description="Identificador del modelo usado.")
    prompt_id: Optional[str] = Field(None, description="ID interno opcional del prompt.")
    subject_id: Optional[str] = Field(None, description="ID opcional del sujeto/usuario.")
    conversation_id: Optional[str] = Field(
        None, description="ID opcional de la conversación (chat, thread...)."
    )
    # Campo opcional para futuro (documentos, system prompt, etc.)
    contexto: Optional[str] = Field(
        None,
        description="Contexto adicional opcional (system prompt, instrucciones, etc.)",
    )


class VerifyRequest(BaseModel):
    document: Dict[str, Any]


class VerifyResponse(BaseModel):
    valid: bool
    verified: bool
    status: str
    errors: list[str] = []
    details: Optional[Dict[str, Any]] = None


# ============================================================================
# FastAPI app
# ============================================================================

app = FastAPI(
    title="IA-HASH API",
    version="1.0.0",
    description="Emite y verifica documentos IA-HASH (hash SHA256 + firma Ed25519).",
)

# CORS abierto para desarrollo. Si quieres, restringe a tu dominio.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "name": "IA-HASH API",
        "version": "1.0.0",
        "standard": IAHASH_VERSION,
        "hash_alg": HASH_ALG,
        "public_key": _public_key_hex(),
    }


@app.get("/public-key")
def public_key():
    """Devuelve la clave pública actual en hex y en PEM."""
    pub_hex = _public_key_hex()
    with open(PUBLIC_KEY_PATH, "rb") as f:
        pub_pem = f.read().decode("utf-8")

    return {
        "algorithm": "Ed25519",
        "public_key_hex": pub_hex,
        "public_key_pem": pub_pem,
        "iahash_version": IAHASH_VERSION,
    }


@app.post("/issue")
def issue_iahash(body: IssueRequest):
    """
    Emite un documento IA-HASH a partir de Prompt + Respuesta.

    1. Normaliza prompt/contexto/respuesta.
    2. Construye JSON canónico.
    3. Calcula hash SHA256.
    4. Firma con Ed25519.
    5. Devuelve el documento IA-HASH listo para guardar/verificar.
    """
    if not body.prompt.strip():
        raise HTTPException(status_code=400, detail="El campo 'prompt' está vacío.")
    if not body.response.strip():
        raise HTTPException(status_code=400, detail="El campo 'response' está vacío.")

    timestamp = datetime.now(timezone.utc).isoformat()

    metadata = {
        "version_standard": IAHASH_VERSION,
        "modelo": body.model or "desconocido",
        "prompt_id": body.prompt_id,
        "subject_id": body.subject_id,
        "conversation_id": body.conversation_id,
        "timestamp": timestamp,
        "hash_alg": HASH_ALG,
    }

    # 1–3. JSON canónico + hash
    payload = canonical_payload(
        prompt=body.prompt,
        contexto=body.contexto,
        respuesta=body.response,
        metadata=metadata,
    )
    canonical_str = canonical_json_str(payload)
    hash_value = compute_hash(canonical_str)

    # 4. Firma
    signature_hex = sign_canonical(canonical_str)
    pub_hex = _public_key_hex()

    document = {
        **payload,
        "hash": hash_value,
        "firma": signature_hex,
        "llave_publica": pub_hex,
    }

    # La web solo necesita el JSON tal cual.
    return document


@app.post("/verify", response_model=VerifyResponse)
def verify_iahash(body: VerifyRequest):
    """
    Verifica un documento IA-HASH:

    - Recalcula el JSON canónico a partir de prompt/contexto/respuesta/metadata.
    - Recalcula el hash y lo compara con `document["hash"]`.
    - Verifica la firma Ed25519 con `document["llave_publica"]` y `document["firma"]`.
    """
    doc = body.document
    errors: list[str] = []

    # Comprobación de campos mínimos
    for field in ("prompt", "respuesta", "metadata", "hash", "firma", "llave_publica"):
        if field not in doc:
            errors.append(f"Falta el campo obligatorio '{field}' en el documento.")

    if errors:
        return VerifyResponse(
            valid=False,
            verified=False,
            status="invalid",
            errors=errors,
        )

    # Reconstruir payload canónico desde el documento proporcionado
    payload = canonical_payload(
        prompt=doc.get("prompt", ""),
        contexto=doc.get("contexto"),
        respuesta=doc.get("respuesta", ""),
        metadata=doc.get("metadata", {}),
    )
    canonical_str = canonical_json_str(payload)
    recomputed_hash = compute_hash(canonical_str)

    stored_hash = doc.get("hash", "")
    if recomputed_hash != stored_hash:
        errors.append("El hash no coincide con el contenido (documento modificado).")

    # Verificar firma
    pub_hex = doc.get("llave_publica", "")
    sig_hex = doc.get("firma", "")

    if not verify_signature(pub_hex, canonical_str, sig_hex):
        errors.append("La firma Ed25519 no es válida para este documento.")

    valid = len(errors) == 0

    return VerifyResponse(
        valid=valid,
        verified=valid,
        status="valid" if valid else "invalid",
        errors=errors,
        details={
            "hash_recomputed": recomputed_hash,
            "hash_stored": stored_hash,
            "iahash_version": doc.get("metadata", {}).get(
                "version_standard", IAHASH_VERSION
            ),
        },
    )
