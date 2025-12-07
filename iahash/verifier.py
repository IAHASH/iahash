"""Verification utilities for IA-HASH v1.2."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from iahash.crypto import normalize_text, sha256_hex, verify_signature
from iahash.issuer import PROTOCOL_VERSION, build_total_hash_string


_PUBLIC_KEY_CACHE: Dict[str, Ed25519PublicKey] = {}


class VerificationStatus:
    VALID = "VALID"
    INVALID_SIGNATURE = "INVALID_SIGNATURE"
    HASH_MISMATCH = "HASH_MISMATCH"
    PROMPT_MISMATCH = "PROMPT_MISMATCH"
    UNREACHABLE_SOURCE = "UNREACHABLE_SOURCE"
    UNKNOWN = "UNKNOWN"


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

    issuer_pk_url = document.get("issuer_pk_url")
    if not issuer_pk_url:
        status = VerificationStatus.UNREACHABLE_SOURCE
        return {
            "valid": False,
            "status": status,
            "signature_valid": False,
            "hash_valid": False,
            "prompt_match": False,
            "errors": ["issuer_pk_url is required"],
        }

    # 1) Cargar clave pública
    try:
        public_key = load_remote_public_key(
            issuer_pk_url, timeout=timeout, use_cache=use_cache, key_cache=key_cache
        )
    except (ValueError, TimeoutError, ConnectionError) as exc:
        status = VerificationStatus.UNREACHABLE_SOURCE
        return {
            "valid": False,
            "status": status,
            "signature_valid": False,
            "hash_valid": False,
            "prompt_match": False,
            "errors": [str(exc)],
        }
    except Exception as exc:  # pragma: no cover - fallback for unexpected errors
        status = VerificationStatus.UNREACHABLE_SOURCE
        return {
            "valid": False,
            "status": status,
            "signature_valid": False,
            "hash_valid": False,
            "prompt_match": False,
            "errors": [f"Unable to fetch public key: {exc}"],
        }

    # 2) Verificar firma
    signature_valid = verify_signature(
        document["h_total"].encode("utf-8"),
        document.get("signature", ""),
        public_key,
    )
    if not signature_valid:
        status = VerificationStatus.INVALID_SIGNATURE
        errors.append("Signature verification failed")

    # 3) Recalcular hashes de prompt/respuesta si tenemos raw text
    h_prompt_expected = document.get("h_prompt")
    h_response_expected = document.get("h_response")

    prompt_match = True

    raw_prompt = document.get("raw_prompt_text")
    if raw_prompt is not None:
        recomputed_prompt = sha256_hex(normalize_text(raw_prompt).encode("utf-8"))
        if recomputed_prompt != h_prompt_expected:
            prompt_match = False
            errors.append("Prompt hash mismatch")

    raw_response = document.get("raw_response_text")
    if raw_response is not None:
        recomputed_response = sha256_hex(normalize_text(raw_response).encode("utf-8"))
        if recomputed_response != h_response_expected:
            prompt_match = False
            errors.append("Response hash mismatch")

    # 4) Recalcular h_total a partir de h_prompt/h_response/model/timestamp
    h_total_recomputed = sha256_hex(
        build_total_hash_string(
            document.get("protocol_version", PROTOCOL_VERSION),
            document.get("prompt_id"),
            h_prompt_expected,
            h_response_expected,
            document.get("model", "unknown"),
            document.get("timestamp", ""),
        ).encode("utf-8")
    )
    hash_valid = h_total_recomputed == document.get("h_total")
    if not hash_valid:
        errors.append("h_total mismatch")

    # 5) Determinar estado final
    if signature_valid and hash_valid and prompt_match:
        status = VerificationStatus.VALID
    elif not signature_valid:
        status = VerificationStatus.INVALID_SIGNATURE
    elif not hash_valid:
        status = VerificationStatus.HASH_MISMATCH
    elif not prompt_match:
        status = VerificationStatus.PROMPT_MISMATCH

    return {
        "valid": status == VerificationStatus.VALID,
        "status": status,
        "signature_valid": signature_valid,
        "hash_valid": hash_valid,
        "prompt_match": prompt_match,
        "errors": errors,
    }
