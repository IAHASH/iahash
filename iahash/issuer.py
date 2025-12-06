from __future__ import annotations

from datetime import datetime, timezone

from .crypto import normalise, sha256_hex, load_private_key, sign_hex
from .models import IAHashDocument
from .paths import private_key_path


VERSION = "IAHASH-1"


def issue_document(
    prompt_text: str,
    respuesta_text: str,
    modelo: str,
    prompt_id: str | None = None,
    subject_id: str | None = None,
    conversation_id: str | None = None,
    timestamp: str | None = None,
    issuer_pk_url: str | None = "https://iahash.com/public-key.pem",
    issuer_id: str = "iahash.com",
) -> IAHashDocument:
    """Create and sign an IA-HASH document for the given prompt + response."""

    if timestamp is None:
        timestamp = datetime.now(timezone.utc).isoformat()

    h_prompt = sha256_hex(normalise(prompt_text))
    h_respuesta = sha256_hex(normalise(respuesta_text))

    cadena_total = "|".join([VERSION, prompt_id or "", h_prompt, h_respuesta, modelo, timestamp])
    h_total = sha256_hex(cadena_total.encode("utf-8"))

    sk = load_private_key(private_key_path())
    firma_total = sign_hex(h_total, sk)

    return IAHashDocument(
        version=VERSION,
        prompt_maestro=prompt_text,
        respuesta=respuesta_text,
        modelo=modelo,
        timestamp=timestamp,
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
