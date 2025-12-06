"""IA-HASH issuer for v1.2 documents."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from iahash.crypto import derive_iah_id, normalize_text, sha256_hex, sign_message
from iahash.db import store_iah_document

PROTOCOL_VERSION = "IAHASH-1.2"


def build_total_hash_string(protocol_version: str, prompt_id: Optional[str], h_prompt: str, h_response: str, model: str, timestamp: str) -> str:
    prompt_value = prompt_id or ""
    model_value = model or "unknown"
    return "|".join([protocol_version, prompt_value, h_prompt, h_response, model_value, timestamp])


def issue_pair(prompt_text: str, response_text: str, *, prompt_id: Optional[str] = None, model: str = "unknown", issuer_id: Optional[str] = None, issuer_pk_url: Optional[str] = None, subject_id: Optional[str] = None, store_raw: bool = False) -> Dict[str, Any]:
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


def issue_conversation(prompt_text: str, response_text: str, *, prompt_id: Optional[str], model: str, conversation_url: str, provider: str, issuer_id: Optional[str] = None, issuer_pk_url: Optional[str] = None, subject_id: Optional[str] = None, store_raw: bool = False) -> Dict[str, Any]:
    return _issue_document(
        prompt_text=prompt_text,
        response_text=response_text,
        prompt_id=prompt_id,
        model=model,
        issuer_id=issuer_id,
        issuer_pk_url=issuer_pk_url,
        subject_id=subject_id,
        store_raw=store_raw,
        doc_type="CONVERSATION",
        mode="TRUSTED_URL",
        conversation_url=conversation_url,
        provider=provider,
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
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    h_prompt = sha256_hex(normalize_text(prompt_text))
    h_response = sha256_hex(normalize_text(response_text))
    h_total_string = build_total_hash_string(PROTOCOL_VERSION, prompt_id, h_prompt, h_response, model, timestamp)
    h_total = sha256_hex(h_total_string)

    issuer_id_final = issuer_id or os.getenv("IAHASH_ISSUER_ID", "iahash.local")
    issuer_pk_url_final = issuer_pk_url or os.getenv(
        "IAHASH_ISSUER_PK_URL", "http://localhost:8000/keys/issuer_ed25519.pub"
    )

    signature = sign_message(h_total.encode("utf-8"))
    iah_id = derive_iah_id(h_total)

    document = {
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

    store_iah_document(document)
    return document
