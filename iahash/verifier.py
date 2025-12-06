from __future__ import annotations

from typing import Tuple
import json

from .crypto import load_public_key, normalise, sha256_hex, verify_signature_hex
from .models import IAHashDocument, LLMID
from .paths import public_key_path


def _context_block(doc: IAHashDocument) -> str:
    payload = {
        "prompt_id": doc.prompt_id,
        "modelo": doc.modelo,
        "timestamp": doc.timestamp,
        "subject": doc.subject,
        "conversation_id": doc.conversation_id,
        "llmid": doc.llmid.model_dump() if isinstance(doc.llmid, LLMID) else doc.llmid,
        "metadata": doc.metadata or {},
        "contexto": None,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def verify_document(doc: IAHashDocument) -> Tuple[bool, str]:
    """Verify integrity and authenticity of an IA-HASH document."""

    h_prompt_local = sha256_hex(normalise(doc.prompt_maestro))
    if h_prompt_local != doc.h_prompt:
        return False, "Prompt Maestro has been modified"

    h_respuesta_local = sha256_hex(normalise(doc.respuesta))
    if h_respuesta_local != doc.h_respuesta:
        return False, "Response has been modified"

    context_serialised = _context_block(doc)
    h_context_local = sha256_hex(normalise(context_serialised))
    if h_context_local != doc.h_contexto:
        return False, "Context has been modified"

    cadena_total = "|".join([doc.version, doc.h_prompt, doc.h_respuesta, doc.h_contexto])
    h_total_local = sha256_hex(cadena_total.encode("utf-8"))
    if h_total_local != doc.h_total:
        return False, "Metadata has been modified"

    pk = load_public_key(public_key_path())
    if not verify_signature_hex(doc.h_total, doc.firma_total, pk):
        return False, "Invalid signature (not issued by declared issuer)"

    return True, "IA-HASH document is valid and unmodified"
