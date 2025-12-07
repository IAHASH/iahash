"""Verification utilities for IA-HASH v1.2."""

from __future__ import annotations

import os
import hmac
from typing import Any, Dict, List, Optional

import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from iahash.crypto import normalize_text, sha256_hex, verify_signature
from iahash.issuer import PROTOCOL_VERSION, build_total_hash_string
from iahash.extractors.chatgpt_share import extract_chatgpt_share
from iahash.extractors.exceptions import UnreachableSource, UnsupportedProvider


_PUBLIC_KEY_CACHE: Dict[str, Ed25519PublicKey] = {}


class VerificationStatus:
    VALID = "VALID"
    INVALID_SIGNATURE = "INVALID_SIGNATURE"
    HASH_MISMATCH = "HASH_MISMATCH"
    PROMPT_MISMATCH = "PROMPT_MISMATCH"
    UNREACHABLE_SOURCE = "UNREACHABLE_SOURCE"
    UNSUPPORTED_PROVIDER = "UNSUPPORTED_PROVIDER"
    UNKNOWN = "UNKNOWN"


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
    status = VerificationStatus.UNKNOWN

    def _fail(status_value: str, error_message: str) -> Dict[str, Any]:
        return {
            "valid": False,
            "status": status_value,
            "signature_valid": False,
            "hash_valid": False,
            "prompt_match": False,
            "prompt_hmac_valid": False,
            "errors": [error_message],
        }

    issuer_pk_url = document.get("issuer_pk_url")
    if not issuer_pk_url:
        status = VerificationStatus.UNREACHABLE_SOURCE
        return _fail(status, "issuer_pk_url is required")

    # 1) Cargar clave pública
    try:
        public_key = load_remote_public_key(
            issuer_pk_url, timeout=timeout, use_cache=use_cache, key_cache=key_cache
        )
    except (ValueError, TimeoutError, ConnectionError) as exc:
        status = VerificationStatus.UNREACHABLE_SOURCE
        return _fail(status, str(exc))
    except Exception as exc:  # pragma: no cover - fallback para errores inesperados
        status = VerificationStatus.UNREACHABLE_SOURCE
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
            status = VerificationStatus.UNREACHABLE_SOURCE
            return _fail(status, f"Conversation URL unreachable: {exc}")
        except UnsupportedProvider as exc:
            status = VerificationStatus.UNSUPPORTED_PROVIDER
            return _fail(status, str(exc))
        except Exception as exc:  # pragma: no cover - extractor defensivo
            status = VerificationStatus.UNREACHABLE_SOURCE
            return _fail(status, f"Unable to fetch conversation: {exc}")

        fetched_prompt = extracted.get("prompt_text")
        fetched_response = extracted.get("response_text")
        fetched_model = extracted.get("model")

    raw_prompt = fetched_prompt if fetched_prompt is not None else document.get("raw_prompt_text")
    raw_response = (
        fetched_response if fetched_response is not None else document.get("raw_response_text")
    )

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
        recomputed_prompt_hash = sha256_hex(normalize_text(raw_prompt).encode("utf-8"))
        if recomputed_prompt_hash != h_prompt_expected:
            prompt_match = False
            errors.append("Prompt hash mismatch")

    if raw_response is not None:
        recomputed_response_hash = sha256_hex(normalize_text(raw_response).encode("utf-8"))
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
        status = VerificationStatus.VALID
    elif not signature_valid:
        status = VerificationStatus.INVALID_SIGNATURE
    elif not prompt_match or not prompt_hmac_valid:
        status = VerificationStatus.PROMPT_MISMATCH
    elif not hash_valid:
        status = VerificationStatus.HASH_MISMATCH

    return {
        "valid": status == VerificationStatus.VALID,
        "status": status,
        "signature_valid": signature_valid,
        "hash_valid": hash_valid,
        "prompt_match": prompt_match,
        "prompt_hmac_valid": prompt_hmac_valid,
        "errors": errors,
    }
