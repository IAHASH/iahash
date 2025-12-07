"""Verification utilities for IA-HASH v1.2."""

from __future__ import annotations

import os
import hmac
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from iahash.crypto import normalize_text, sha256_hex, verify_signature
from iahash.config import ISSUER_ID, ISSUER_PK_URL
from iahash.issuer import PROTOCOL_VERSION, build_total_hash_string
from iahash.extractors.chatgpt_share import extract_chatgpt_share
from iahash.extractors.exceptions import UnreachableSource, UnsupportedProvider


_PUBLIC_KEY_CACHE: Dict[str, Ed25519PublicKey] = {}


class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    INVALID_SIGNATURE = "INVALID_SIGNATURE"
    UNREACHABLE_ISSUER = "UNREACHABLE_ISSUER"
    MALFORMED_DOCUMENT = "MALFORMED_DOCUMENT"
    UNSUPPORTED_PROVIDER = "UNSUPPORTED_PROVIDER"


SUPPORTED_PROVIDERS = {"chatgpt"}


def load_remote_public_key(
    url: str,
    *,
    timeout: float = 10.0,
    key_cache: Optional[Dict[str, Ed25519PublicKey]] = None,
    use_cache: bool = False,
) -> Ed25519PublicKey:
    """
    Descarga y carga una clave pública Ed25519 desde una URL (PEM).
    """
    if not url:
        raise ValueError("issuer_pk_url is required")

    cache_store = key_cache if key_cache is not None else (_PUBLIC_KEY_CACHE if use_cache else None)
    if cache_store is not None and url in cache_store:
        return cache_store[url]

    try:
        response = httpx.get(url, timeout=timeout)
        response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise TimeoutError(f"Timeout fetching issuer public key from {url}") from exc
    except httpx.HTTPStatusError as exc:
        raise ConnectionError(
            f"Failed to fetch issuer public key from {url}: {exc.response.status_code}"
        ) from exc
    except httpx.RequestError as exc:
        raise ConnectionError(f"Unable to fetch issuer public key from {url}: {exc}") from exc

    data = response.content
    public_key = serialization.load_pem_public_key(data)

    if cache_store is not None:
        cache_store[url] = public_key

    return public_key


def verify_document(
    document: Dict[str, Any],
    *,
    timeout: float = 10.0,
    use_cache: bool = False,
    key_cache: Optional[Dict[str, Ed25519PublicKey]] = None,
) -> Dict[str, Any]:
    """
    Verifica un documento IA-HASH completo.

    Pasos:
      1. Descargar clave pública del issuer (issuer_pk_url).
      2. Verificar firma Ed25519 sobre h_total.
      3. Recalcular hashes de prompt/respuesta si hay raw_text.
      4. Recalcular h_total a partir de h_prompt/h_response/model/timestamp.
      5. Devolver estado + flags de validez y lista de errores.
    """
    errors: List[str] = []
    status = VerificationStatus.MALFORMED_DOCUMENT
    differences: Optional[Dict[str, Any]] = None
    status_detail: Optional[str] = None

    def _fail(status_value: VerificationStatus, error_message: str) -> Dict[str, Any]:
        return {
            "valid": False,
            "status": status_value.value,
            "status_detail": status_detail,
            "signature_valid": False,
            "hash_valid": False,
            "prompt_match": False,
            "prompt_hmac_valid": False,
            "errors": [error_message],
            "resolved_issuer_pk_url": None,
        }

    issuer_id = document.get("issuer_id")
    issuer_pk_url = document.get("issuer_pk_url")
    if not issuer_pk_url:
        if issuer_id and issuer_id == ISSUER_ID:
            issuer_pk_url = ISSUER_PK_URL
        else:
            status = VerificationStatus.MALFORMED_DOCUMENT
            status_detail = "MISSING_ISSUER_PK_URL"
            return _fail(
                status,
                "Missing issuer_pk_url and issuer_id does not match local issuer",
            )

    # 1) Cargar clave pública
    try:
        public_key = load_remote_public_key(
            issuer_pk_url, timeout=timeout, use_cache=use_cache, key_cache=key_cache
        )
    except (ValueError, TimeoutError, ConnectionError) as exc:
        status = VerificationStatus.UNREACHABLE_ISSUER
        return _fail(status, str(exc))
    except Exception as exc:  # pragma: no cover - fallback para errores inesperados
        status = VerificationStatus.UNREACHABLE_ISSUER
        return _fail(status, f"Unable to fetch public key: {exc}")

    # 2) Resolver textos del prompt/respuesta
    provider = (document.get("provider") or "").lower()
    conversation_url = document.get("conversation_url")
    fetched_prompt: Optional[str] = None
    fetched_response: Optional[str] = None
    fetched_model: Optional[str] = None

    if conversation_url and provider:
        if provider not in SUPPORTED_PROVIDERS:
            status = VerificationStatus.UNSUPPORTED_PROVIDER
            return _fail(status, f"Provider not supported: {provider}")

        try:
            extracted = extract_chatgpt_share(conversation_url)
        except UnreachableSource as exc:
            status = VerificationStatus.UNREACHABLE_ISSUER
            return _fail(status, f"Conversation URL unreachable: {exc}")
        except UnsupportedProvider as exc:
            status = VerificationStatus.UNSUPPORTED_PROVIDER
            return _fail(status, str(exc))
        except Exception as exc:  # pragma: no cover - extractor defensivo
            status = VerificationStatus.UNREACHABLE_ISSUER
            return _fail(status, f"Unable to fetch conversation: {exc}")

        fetched_prompt = extracted.get("prompt_text")
        fetched_response = extracted.get("response_text")
        fetched_model = extracted.get("model")

    raw_prompt = fetched_prompt if fetched_prompt is not None else document.get("raw_prompt_text")
    raw_response = (
        fetched_response if fetched_response is not None else document.get("raw_response_text")
        )

    resolved_issuer_pk_url = issuer_pk_url

    normalized_prompt_text: Optional[str] = None
    normalized_response_text: Optional[str] = None

    h_prompt_expected = document.get("h_prompt")
    h_response_expected = document.get("h_response")

    # 3) Verificar firma sobre h_total provisto
    signature_hex = document.get("signature", "")
    try:
        signature_bytes = bytes.fromhex(signature_hex)
    except ValueError:
        signature_bytes = b""

    signature_valid = verify_signature(
        document.get("h_total", "").encode("utf-8"), signature_bytes, public_key
    )
    if not signature_valid:
        errors.append("Signature verification failed")

    # 4) Recalcular hashes de prompt/respuesta si tenemos raw text
    prompt_match = True
    recomputed_prompt_hash: Optional[str] = None
    recomputed_response_hash: Optional[str] = None

    if raw_prompt is not None:
        normalized_prompt_text = normalize_text(raw_prompt)
        recomputed_prompt_hash = sha256_hex(normalized_prompt_text.encode("utf-8"))
        if recomputed_prompt_hash != h_prompt_expected:
            prompt_match = False
            errors.append("Prompt hash mismatch")

    if raw_response is not None:
        normalized_response_text = normalize_text(raw_response)
        recomputed_response_hash = sha256_hex(normalized_response_text.encode("utf-8"))
        if recomputed_response_hash != h_response_expected:
            prompt_match = False
            errors.append("Response hash mismatch")

    # 5) Recalcular h_total a partir de h_prompt/h_response/model/timestamp
    final_h_prompt = recomputed_prompt_hash or h_prompt_expected or ""
    final_h_response = recomputed_response_hash or h_response_expected or ""
    model_value = fetched_model or document.get("model", "unknown")

    h_total_recomputed = sha256_hex(
        build_total_hash_string(
            document.get("protocol_version", PROTOCOL_VERSION),
            document.get("prompt_id"),
            final_h_prompt,
            final_h_response,
            model_value,
            document.get("timestamp", ""),
        ).encode("utf-8")
    )
    hash_valid = h_total_recomputed == document.get("h_total")
    if not hash_valid:
        errors.append("h_total mismatch")

    # 6) Verificación opcional de HMAC del prompt maestro
    prompt_hmac_valid = True
    prompt_hmac = document.get("prompt_hmac")
    prompt_hmac_key = os.getenv("IAHASH_PROMPT_HMAC_KEY")
    if prompt_hmac and prompt_hmac_key and raw_prompt is not None:
        computed_hmac = hmac.new(
            prompt_hmac_key.encode("utf-8"),
            normalize_text(raw_prompt).encode("utf-8"),
            "sha256",
        ).hexdigest()
        prompt_hmac_valid = computed_hmac == prompt_hmac
        if not prompt_hmac_valid:
            errors.append("Prompt HMAC mismatch")

    # 7) Determinar estado final
    if signature_valid and hash_valid and prompt_match and prompt_hmac_valid:
        status = VerificationStatus.VERIFIED
    elif not prompt_match or not prompt_hmac_valid:
        status = VerificationStatus.INVALID_SIGNATURE
        status_detail = "CONTENT_MISMATCH"
    elif not signature_valid or not hash_valid:
        status = VerificationStatus.INVALID_SIGNATURE
        status_detail = "SIGNATURE_MISMATCH" if not signature_valid else "HASH_MISMATCH"

    if status == VerificationStatus.INVALID_SIGNATURE:
        differences = {"hashes": {}, "fields": {}}  # type: ignore[assignment]

        def add_diff(category: str, key: str, expected: Any, computed: Any) -> None:
            if expected is None and computed is None:
                return
            differences_category = differences.setdefault(category, {})  # type: ignore[assignment]
            differences_category[key] = {"expected": expected, "computed": computed}

        add_diff("hashes", "h_prompt", h_prompt_expected, recomputed_prompt_hash)
        add_diff("hashes", "h_response", h_response_expected, recomputed_response_hash)
        add_diff("hashes", "h_total", document.get("h_total"), h_total_recomputed)

        expected_model = document.get("model", "unknown")
        add_diff("fields", "model", expected_model, model_value)
        add_diff("fields", "timestamp", document.get("timestamp"), document.get("timestamp"))
        add_diff("fields", "prompt_id", document.get("prompt_id"), document.get("prompt_id"))
        add_diff("fields", "provider", document.get("provider"), document.get("provider"))
        add_diff(
            "fields",
            "prompt_hmac",
            document.get("prompt_hmac"),
            document.get("prompt_hmac"),
        )
        add_diff(
            "fields",
            "prompt_hmac_valid",
            bool(document.get("prompt_hmac")) if prompt_hmac else None,
            prompt_hmac_valid if prompt_hmac else None,
        )
        differences["inputs_for_total"] = {
            "protocol_version": document.get("protocol_version", PROTOCOL_VERSION),
            "prompt_id": document.get("prompt_id"),
            "h_prompt": final_h_prompt,
            "h_response": final_h_response,
            "model": model_value,
            "timestamp": document.get("timestamp", ""),
        }

    return {
        "valid": status == VerificationStatus.VERIFIED,
        "status": status.value,
        "status_detail": status_detail,
        "signature_valid": signature_valid,
        "hash_valid": hash_valid,
        "prompt_match": prompt_match,
        "prompt_hmac_valid": prompt_hmac_valid,
        "errors": errors,
        "normalized_prompt_text": normalized_prompt_text,
        "normalized_response_text": normalized_response_text,
        "differences": differences,
        "resolved_issuer_pk_url": resolved_issuer_pk_url,
    }
