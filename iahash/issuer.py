"""IA-HASH issuer for v1.2 documents."""

from __future__ import annotations

import hmac
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from iahash.config import ISSUER_ID, ISSUER_PK_URL
from iahash.crypto import (
    PROTOCOL_VERSION as CRYPTO_PROTOCOL_VERSION,
    compute_pair_hashes,
    derive_iah_id,
    load_ed25519_private_key,
    normalize_text,
    sha256_hex,
    sign_message,
)
from iahash.db import get_prompt_by_id, get_prompt_by_slug, store_iah_document
from iahash.extractors.chatgpt_share import (
    ERROR_PARSING,
    ERROR_UNREACHABLE,
    ERROR_UNSUPPORTED,
    extract_chatgpt_share,
)
from iahash.extractors.exceptions import UnreachableSource, UnsupportedProvider

# Re-export para compatibilidad con otros módulos (p.ej. verifier)
PROTOCOL_VERSION = CRYPTO_PROTOCOL_VERSION


def _compute_prompt_hmac(prompt_text: str, *, secret_key: str) -> str:
    normalized = normalize_text(prompt_text)
    return hmac.new(secret_key.encode("utf-8"), normalized.encode("utf-8"), "sha256").hexdigest()


def _get_prompt_record(prompt_id: str | int) -> Optional[Dict[str, Any]]:
    prompt_pk: Optional[int]
    try:
        prompt_pk = int(prompt_id)
    except (TypeError, ValueError):
        prompt_pk = None

    try:
        if prompt_pk is not None:
            prompt = get_prompt_by_id(prompt_pk)
            if prompt:
                return prompt
    except sqlite3.Error:
        return None

    try:
        return get_prompt_by_slug(str(prompt_id))
    except sqlite3.Error:
        return None


def _validate_master_prompt(prompt: Dict[str, Any], prompt_text: str) -> Tuple[str, str]:
    if not prompt:
        raise ValueError("Prompt maestro no encontrado")
    if not prompt.get("is_master"):
        raise ValueError("El prompt indicado no está marcado como maestro")

    stored_prompt_text = prompt.get("full_prompt") or ""
    normalized_input = normalize_text(prompt_text)
    normalized_master = normalize_text(stored_prompt_text)

    if normalized_input != normalized_master:
        raise ValueError("El texto proporcionado no coincide con el prompt maestro")

    computed_public = sha256_hex(normalized_master.encode("utf-8"))
    stored_public = prompt.get("h_public")
    if stored_public and stored_public != computed_public:
        # Respetamos el hash público registrado aunque no coincida con el
        # calculado, para mantener compatibilidad con seeds existentes.
        computed_public = stored_public

    hmac_key = os.getenv("IAHASH_PROMPT_HMAC_KEY")
    if not hmac_key:
        raise ValueError("IAHASH_PROMPT_HMAC_KEY requerido para validar prompt maestro")

    computed_secret = _compute_prompt_hmac(normalized_master, secret_key=hmac_key)
    stored_secret = prompt.get("h_secret")
    if stored_secret and stored_secret != computed_secret:
        raise ValueError("h_secret almacenado no coincide con el prompt maestro")

    return computed_public, computed_secret


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
        raise RuntimeError("Unsupported conversation format") from exc
    if extracted.get("error"):
        detail = extracted["error"]
        if detail == ERROR_UNREACHABLE:
            raise RuntimeError("Conversation URL unreachable")
        if detail == ERROR_PARSING:
            raise RuntimeError("Conversation content could not be parsed")
        if detail == ERROR_UNSUPPORTED:
            raise RuntimeError("Unsupported conversation format")
        raise RuntimeError(detail)

    extracted_prompt = extracted.get("prompt_text") or prompt_text
    extracted_response = extracted.get("response_text") or response_text
    extracted_model = extracted.get("model") or model
    extracted_provider = extracted.get("provider") or provider

    if prompt_id is not None and prompt_text is not None:
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


def issue_from_share(
    *,
    prompt_text: str,
    response_text: str,
    model: str,
    share_url: str,
    prompt_id: Optional[str] = None,
    subject_id: Optional[str] = None,
    issuer_id: Optional[str] = None,
    issuer_pk_url: Optional[str] = None,
    store_raw: bool = False,
) -> Dict[str, Any]:
    """Emite un IA-HASH a partir de un enlace compartido de chat."""

    return _issue_document(
        prompt_text=prompt_text,
        response_text=response_text,
        prompt_id=prompt_id,
        model=model or "chatgpt",
        issuer_id=issuer_id,
        issuer_pk_url=issuer_pk_url,
        subject_id=subject_id,
        store_raw=store_raw,
        doc_type="CONVERSATION",
        mode="TRUSTED_URL",
        conversation_url=share_url,
        provider="chatgpt",
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

    prompt_public_hash: Optional[str] = None
    prompt_hmac: Optional[str] = None
    prompt_hmac_verified = False
    prompt_id_value: Optional[str] = None

    prompt_record = _get_prompt_record(prompt_id) if prompt_id is not None else None

    if prompt_record:
        prompt_public_hash, prompt_hmac = _validate_master_prompt(prompt_record, prompt_text)
        prompt_hmac_verified = True
        prompt_id_value = str(prompt_record.get("id") or prompt_id)
    elif prompt_id is not None:
        prompt_id_value = str(prompt_id)

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
        prompt_id=prompt_id_value,
        model=model,
        timestamp=timestamp,
    )
    h_prompt = pair_hashes.h_prompt
    h_response = pair_hashes.h_response
    h_total = pair_hashes.h_total

    # Datos del emisor (issuer)
    issuer_id_final = (issuer_id or ISSUER_ID) or ISSUER_ID
    issuer_pk_url_final = issuer_pk_url if issuer_pk_url not in ("", None) else None
    if issuer_pk_url_final is None:
        issuer_pk_url_final = ISSUER_PK_URL

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
        "prompt_id": prompt_id_value,
        "prompt_hmac": prompt_hmac,
        "prompt_hmac_verified": prompt_hmac_verified,
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

    if prompt_public_hash:
        document["prompt_public_hash"] = prompt_public_hash

    # Persistimos en SQLite (tabla iahash_documents)
    store_iah_document(document)

    return document
