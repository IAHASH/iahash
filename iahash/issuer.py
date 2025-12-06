from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Optional

from .crypto import load_private_key, normalise, sha256_hex, sign_hex
from .models import IAHashDocument, LLMID
from .paths import private_key_path

VERSION = "IAHASH-1"


def _timestamp_or_now(timestamp: Optional[str]) -> str:
    if timestamp:
        return timestamp
    now = datetime.now(timezone.utc).replace(microsecond=0)
    return now.isoformat().replace("+00:00", "Z")


def _context_block(
    *,
    prompt_id: Optional[str],
    modelo: str,
    timestamp: str,
    subject: Optional[str],
    conversation_id: Optional[str],
    llmid: Optional[LLMID],
    metadata: dict,
    contexto: Optional[str],
) -> str:
    context_payload = {
        "prompt_id": prompt_id,
        "modelo": modelo,
        "timestamp": timestamp,
        "subject": subject,
        "conversation_id": conversation_id,
        "llmid": llmid.model_dump() if llmid else None,
        "metadata": metadata or {},
        "contexto": contexto,
    }
    return json.dumps(context_payload, sort_keys=True, separators=(",", ":"))


def issue_document(
    *,
    prompt_text: str,
    respuesta_text: str,
    modelo: Optional[str],
    prompt_id: Optional[str] = None,
    subject: Optional[str] = None,
    conversation_id: Optional[str] = None,
    timestamp: Optional[str] = None,
    llmid: Optional[LLMID] = None,
    metadata: Optional[dict] = None,
    contexto: Optional[str] = None,
    issuer_pk_url: Optional[str] = "https://iahash.com/public-key.pem",
    issuer_id: str = "iahash.com",
) -> IAHashDocument:
    """Create and sign an IA-HASH document for the given prompt + response."""

    timestamp_value = _timestamp_or_now(timestamp)
    modelo_value = modelo or "unknown"
    metadata_value = metadata or {}

    h_prompt = sha256_hex(normalise(prompt_text))
    h_respuesta = sha256_hex(normalise(respuesta_text))
    contexto_serialised = _context_block(
        prompt_id=prompt_id,
        modelo=modelo_value,
        timestamp=timestamp_value,
        subject=subject,
        conversation_id=conversation_id,
        llmid=llmid,
        metadata=metadata_value,
        contexto=contexto,
    )
    h_contexto = sha256_hex(normalise(contexto_serialised))

    cadena_total = "|".join([VERSION, h_prompt, h_respuesta, h_contexto])
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
        subject=subject,
        conversation_id=conversation_id,
        llmid=llmid,
        metadata=metadata_value,
        h_prompt=h_prompt,
        h_respuesta=h_respuesta,
        h_contexto=h_contexto,
        h_total=h_total,
        firma_total=firma_total,
        issuer_pk_url=issuer_pk_url,
        issuer_id=issuer_id,
    )
