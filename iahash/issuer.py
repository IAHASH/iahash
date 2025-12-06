from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from .crypto import load_private_key, normalise, sha256_hex, sign_hex
from .models import IAHashDocument
from .paths import private_key_path

VERSION = "IAHASH-1"


def _timestamp_or_now(timestamp: Optional[str]) -> str:
    if timestamp:
        return timestamp
    now = datetime.now(timezone.utc).replace(microsecond=0)
    return now.isoformat().replace("+00:00", "Z")


def issue_document(
    *,
    prompt_text: str,
    respuesta_text: str,
    modelo: Optional[str],
    prompt_id: Optional[str] = None,
    subject_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
    timestamp: Optional[str] = None,
    issuer_pk_url: Optional[str] = "https://iahash.com/public-key.pem",
    issuer_id: str = "iahash.com",
) -> IAHashDocument:
    """Create and sign an IA-HASH document for the given prompt + response."""

    timestamp_value = _timestamp_or_now(timestamp)
    modelo_value = modelo or "unknown"

    h_prompt = sha256_hex(normalise(prompt_text))
    h_respuesta = sha256_hex(normalise(respuesta_text))

    cadena_total = "|".join([VERSION, prompt_id or "", h_prompt, h_respuesta, modelo_value, timestamp_value])
    h_total = sha256_hex(cadena_total.encode("utf-8"))

    sk = load_private_key(private_key_path())
    firma_total = sign_hex(h_total, sk)

    return IAHashDocument(
        version=VERSION,
        prompt_maestro=prompt_text,
        respuesta=respuesta_text,
        modelo=modelo_value,
        timestamp=timestamp_value,
        prompt_id=prompt_id,
        subject_id=subject_id,
        conversation_id=conversation_id,
        h_prompt=h_prompt,
        h_respuesta=h_respuesta,
        h_total=h_total,
        firma_total=firma_total,
        issuer_pk_url=issuer_pk_url,
        issuer_id=issuer_id,
    )
