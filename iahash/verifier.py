"""Verification utilities for IA-HASH v1.2."""

from __future__ import annotations

from typing import Any, Dict

import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from iahash.crypto import normalize_text, sha256_hex, verify_signature
from iahash.issuer import PROTOCOL_VERSION, build_total_hash_string


class VerificationStatus:
    VALID = "VALID"
    INVALID_SIGNATURE = "INVALID_SIGNATURE"
    HASH_MISMATCH = "HASH_MISMATCH"
    PROMPT_MISMATCH = "PROMPT_MISMATCH"
    UNREACHABLE_SOURCE = "UNREACHABLE_SOURCE"
    UNKNOWN = "UNKNOWN"


def load_remote_public_key(url: str) -> Ed25519PublicKey:
    response = httpx.get(url, timeout=10)
    response.raise_for_status()
    data = response.content
    return serialization.load_pem_public_key(data)


def verify_document(document: Dict[str, Any]) -> Dict[str, Any]:
    errors: list[str] = []
    status = VerificationStatus.UNKNOWN

    try:
        public_key = load_remote_public_key(document["issuer_pk_url"])
    except Exception:
        status = VerificationStatus.UNREACHABLE_SOURCE
        return {
            "valid": False,
            "status": status,
            "signature_valid": False,
            "hash_valid": False,
            "prompt_match": False,
            "errors": ["Unable to fetch public key"],
        }

    signature_valid = verify_signature(
        document["h_total"].encode("utf-8"), document.get("signature", ""), public_key
    )
    if not signature_valid:
        status = VerificationStatus.INVALID_SIGNATURE
        errors.append("Signature verification failed")

    h_prompt_expected = document.get("h_prompt")
    h_response_expected = document.get("h_response")

    # recompute hashes when raw text exists
    prompt_match = True
    if document.get("raw_prompt_text") is not None:
        recomputed_prompt = sha256_hex(normalize_text(document["raw_prompt_text"]))
        if recomputed_prompt != h_prompt_expected:
            prompt_match = False
            errors.append("Prompt hash mismatch")
    if document.get("raw_response_text") is not None:
        recomputed_response = sha256_hex(normalize_text(document["raw_response_text"]))
        if recomputed_response != h_response_expected:
            prompt_match = False
            errors.append("Response hash mismatch")

    h_total_recomputed = sha256_hex(
        build_total_hash_string(
            document.get("protocol_version", PROTOCOL_VERSION),
            document.get("prompt_id"),
            h_prompt_expected,
            h_response_expected,
            document.get("model", "unknown"),
            document.get("timestamp", ""),
        )
    )
    hash_valid = h_total_recomputed == document.get("h_total")
    if not hash_valid:
        errors.append("h_total mismatch")

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
