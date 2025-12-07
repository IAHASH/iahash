"""IA-HASH issuer for v1.2 documents."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from iahash.crypto import (
    PROTOCOL_VERSION as CRYPTO_PROTOCOL_VERSION,
    compute_pair_hashes,
    derive_iah_id,
    load_ed25519_private_key,
    normalize_text,
    sign_message,
)
from iahash.db import store_iah_document
from iahash.extractors.chatgpt_share import extract_chatgpt_share
from iahash.extractors.exceptions import UnreachableSource, UnsupportedProvider

# Re-export para compatibilidad con otros módulos (p.ej. verifier)
PROTOCOL_VERSION = CRYPTO_PROTOCOL_VERSION


def build_total_hash_string(
    protocol_version: str,
    prompt_id: Optional[str],
    h_prompt: str,
    h_response: str,
    model: str,
    timestamp: str,
) -> str:
    """
    Helper usado tanto en issuer como en verifier.

    Representa exactamente el string que luego se hashea con SHA256 para producir h_total.
    """
    prompt_value = prompt_id or ""
    model_value = model or "unknown"
    return "|".join(
        [
            protocol_version,
            prompt_value,
            h_prompt,
            h_response,
            model_value,
            timestamp,
        ]
    )


def issue_pair(
    prompt_text: str,
    response_text: str,
    *,
    prompt_id: Optional[str] = None,
    model: str = "unknown",
    issuer_id: Optional[str] = None,
    issuer_pk_url: Optional[str] = None,
    subject_id: Optional[str] = None,
    store_raw: bool = False,
) -> Dict[str, Any]:
    """
    Emite un documento IA-HASH tipo PAIR (prompt + respuesta local).
    """
    return _issue_document(
        prompt_text=prompt_text,
        response_text=response_text,
        prompt_id=prompt_id,
        model=model,
        issuer_id=issuer_id,
        issuer_pk_url=issuer_pk_url,
        subject_id=subject_id,
        store_raw=store_raw,
        doc_type="PAIR",
        mode="LOCAL",
        conversation_url=None,
        provider=None,
    )


def issue_conversation(
    prompt_text: str,
    response_text: str,
    *,
    prompt_id: Optional[str],
    model: str,
    conversation_url: str,
    provider: str,
    issuer_id: Optional[str] = None,
    issuer_pk_url: Optional[str] = None,
    subject_id: Optional[str] = None,
    store_raw: bool = False,
) -> Dict[str, Any]:
    """
    Emite un documento IA-HASH tipo CONVERSATION, basado en una URL compartida
    (p.ej. conversación de ChatGPT).
    """
    if provider and provider.lower() != "chatgpt":
        raise ValueError("Unsupported conversation provider")

    try:
        extracted = extract_chatgpt_share(conversation_url)
    except UnreachableSource as exc:
        raise RuntimeError("Conversation URL unreachable") from exc
    except UnsupportedProvider as exc:
        raise ValueError(str(exc)) from exc

    extracted_prompt = extracted.get("prompt_text") or prompt_text
    extracted_response = extracted.get("response_text") or response_text
    extracted_model = extracted.get("model") or model
    extracted_provider = extracted.get("provider") or provider

    if prompt_id is not None:
        if normalize_text(prompt_text) != normalize_text(extracted_prompt):
            raise ValueError("Extracted prompt does not match master prompt")

    return _issue_document(
        prompt_text=extracted_prompt,
        response_text=extracted_response,
        prompt_id=prompt_id,
        model=extracted_model,
        issuer_id=issuer_id,
        issuer_pk_url=issuer_pk_url,
        subject_id=subject_id,
        store_raw=store_raw,
        doc_type="CONVERSATION",
        mode="TRUSTED_URL",
        conversation_url=conversation_url,
        provider=extracted_provider,
    )


def _issue_document(
    *,
    prompt_text: str,
    response_text: str,
    prompt_id: Optional[str],
    model: str,
    issuer_id: Optional[str],
    issuer_pk_url: Optional[str],
    subject_id: Optional[str],
    store_raw: bool,
    doc_type: str,
    mode: str,
    conversation_url: Optional[str],
    provider: Optional[str],
) -> Dict[str, Any]:
    """
    Función interna común a issue_pair / issue_conversation.
    """

    # Timestamp en UTC, sin microsegundos, con sufijo Z
    timestamp = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    # Hashes IA-HASH oficiales (h_prompt, h_response, h_total)
    pair_hashes = compute_pair_hashes(
        prompt_text=prompt_text,
        response_text=response_text,
        protocol_version=PROTOCOL_VERSION,
        prompt_id=prompt_id,
        model=model,
        timestamp=timestamp,
    )
    h_prompt = pair_hashes.h_prompt
    h_response = pair_hashes.h_response
    h_total = pair_hashes.h_total

    # Datos del emisor (issuer)
    issuer_id_final = issuer_id or os.getenv("IAHASH_ISSUER_ID", "iahash.local")
    issuer_pk_url_final = issuer_pk_url or os.getenv(
        "IAHASH_ISSUER_PK_URL",
        "http://localhost:8000/keys/issuer_ed25519.pub",
    )

    # Firma Ed25519 sobre h_total (como string hex)
    private_key = load_ed25519_private_key()
    signature_bytes = sign_message(h_total.encode("utf-8"), private_key)
    signature = signature_bytes.hex()

    # ID público IA-HASH
    iah_id = derive_iah_id(h_total)

    document: Dict[str, Any] = {
        "protocol_version": PROTOCOL_VERSION,
        "type": doc_type,
        "mode": mode,
        "prompt_id": prompt_id,
        "prompt_hmac_verified": prompt_id is not None,
        "timestamp": timestamp,
        "model": model,
        "h_prompt": h_prompt,
        "h_response": h_response,
        "h_total": h_total,
        "signature": signature,
        "issuer_id": issuer_id_final,
        "issuer_pk_url": issuer_pk_url_final,
        "conversation_url": conversation_url,
        "provider": provider,
        "subject_id": subject_id,
        "store_raw": bool(store_raw),
        "raw_prompt_text": prompt_text if store_raw else None,
        "raw_response_text": response_text if store_raw else None,
        "iah_id": iah_id,
    }

    # Persistimos en SQLite (tabla iahash_documents)
    store_iah_document(document)

    return document
