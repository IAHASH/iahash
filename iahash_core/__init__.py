"""IAHASH-PAIR-1 reference cryptography. Pure operations; no storage or network.

Receipt signatures attest to an issuer's assertion about an ordered pair of
hashes. They do not establish truth, causation, source authorship or trusted time.
"""
from __future__ import annotations

import base64
import binascii
from datetime import datetime
import hashlib
import json
import re
import unicodedata
from uuid import UUID

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

PROTOCOL_VERSION = "IAHASH-PAIR-1"
TEXT_PROFILE = "text-nfc-lf-rstrip-v1"
BYTES_PROFILE = "bytes-v1"
UNICODE_VERSION = "15.0.0"
PAIR_DOMAIN = b"IAHASH:PAIR:1\x00"
CERTIFICATE_DOMAIN = b"IAHASH:CERTIFICATE:1\x00"
ENVIRONMENTS = frozenset({"LAB", "STAGING", "PRODUCTION"})
_HEX64 = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
_HEX128 = re.compile(r"[0-9a-f]{128}\Z", re.ASCII)
_ISSUER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}\Z", re.ASCII)
_TIMESTAMP = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{6}Z\Z", re.ASCII)
_BODY_FIELDS = {
    "protocol_version", "hash_algorithm", "signature_algorithm", "issuer_id",
    "key_id", "environment", "receipt_id", "received_at", "evidence", "pair", "pair_id",
}
_FAILURE_PRIORITY = (
    "MALFORMED_CERTIFICATE", "UNSUPPORTED_VERSION", "KEY_UNAVAILABLE",
    "INVALID_SIGNATURE", "KEY_REVOKED", "UNTRUSTED_ISSUER",
    "ENVIRONMENT_MISMATCH", "INVALID_PAIR_BINDING", "CONTENT_MISMATCH",
)


class CoreValidationError(ValueError):
    """Invalid input with a stable machine-readable code."""

    def __init__(self, message: str, code: str = "MALFORMED_CERTIFICATE") -> None:
        super().__init__(message)
        self.code = code


def _require(condition: bool, message: str, code: str = "MALFORMED_CERTIFICATE") -> None:
    if not condition:
        raise CoreValidationError(message, code)


def _fields(value: object, fields: set[str], label: str) -> None:
    _require(type(value) is dict, f"{label} must be an object")
    _require(set(value) == fields, f"{label} must contain exactly {sorted(fields)}")


def _matches(value: object, pattern: re.Pattern, label: str) -> None:
    _require(type(value) is str and pattern.fullmatch(value) is not None, f"Invalid {label}")


def strict_json_loads(data: bytes | str) -> dict:
    """Parse a JSON object, rejecting duplicate keys, invalid UTF-8 and NaN."""
    def pairs(items: list) -> dict:
        result = {}
        for name, value in items:
            _require(name not in result, "Duplicate JSON key")
            result[name] = value
        return result

    def reject_constant(value: str) -> None:
        raise CoreValidationError(f"Invalid JSON constant: {value}")

    _require(type(data) in (str, bytes), "JSON input must be str or bytes")
    try:
        if type(data) is bytes:
            data = data.decode("utf-8", errors="strict")
        value = json.loads(data, object_pairs_hook=pairs, parse_constant=reject_constant)
    except CoreValidationError:
        raise
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise CoreValidationError("Invalid JSON object") from exc
    _require(type(value) is dict, "JSON top level must be an object")
    return value


def canonical_bytes(value: dict) -> bytes:
    """Encode the restricted ASCII object/string vocabulary; this is not JCS."""
    def validate(item: object, depth: int = 0) -> None:
        _require(depth <= 8, "Canonical object is too deeply nested")
        if type(item) is str:
            _require(item.isascii(), "Canonical strings must be ASCII")
        else:
            _require(type(item) is dict, "Canonical values must be objects or ASCII strings")
            for name, child in item.items():
                _require(type(name) is str and name.isascii(), "Canonical keys must be ASCII strings")
                validate(child, depth + 1)

    _require(type(value) is dict, "Canonical top level must be an object")
    validate(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")


def validate_pair(pair: dict) -> dict:
    _fields(pair, {"protocol_version", "par1", "par2"}, "pair")
    _require(type(pair["protocol_version"]) is str, "protocol_version must be a string")
    _require(pair["protocol_version"] == PROTOCOL_VERSION, "Unsupported protocol version", "UNSUPPORTED_VERSION")
    for name in ("par1", "par2"):
        element = pair[name]
        _fields(element, {"profile", "hash"}, name)
        _require(type(element["profile"]) is str and element["profile"] in (TEXT_PROFILE, BYTES_PROFILE), "Unsupported element profile")
        _matches(element["hash"], _HEX64, f"{name}.hash")
    return pair


def _text_bytes(value: str) -> bytes:
    _require(type(value) is str, "Text element must be str")
    _require(unicodedata.unidata_version == UNICODE_VERSION, "Text profile requires Unicode 15.0.0", "UNSUPPORTED_UNICODE_VERSION")
    try:
        value.encode("utf-8", errors="strict")  # Reject isolated surrogates before normalization.
    except UnicodeError as exc:
        raise CoreValidationError("Text contains an isolated Unicode surrogate") from exc
    normalized = unicodedata.normalize("NFC", value).replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip(" \t") for line in normalized.split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines).encode("utf-8")


def hash_element(value: str | bytes, profile: str) -> dict:
    _require(type(profile) is str, "Profile must be a string")
    if profile == TEXT_PROFILE:
        encoded = _text_bytes(value)
    elif profile == BYTES_PROFILE:
        _require(type(value) is bytes, "Bytes element must be bytes")
        encoded = value
    else:
        raise CoreValidationError("Unsupported element profile")
    return {"profile": profile, "hash": hashlib.sha256(encoded).hexdigest()}


def make_pair(par1: str | bytes, par2: str | bytes, *, profile1: str = TEXT_PROFILE, profile2: str = TEXT_PROFILE) -> dict:
    return {
        "protocol_version": PROTOCOL_VERSION,
        "par1": hash_element(par1, profile1),
        "par2": hash_element(par2, profile2),
    }


def derive_pair_id(pair: dict) -> str:
    return hashlib.sha256(PAIR_DOMAIN + canonical_bytes(validate_pair(pair))).hexdigest()


def key_id(public_key: Ed25519PublicKey) -> str:
    _require(isinstance(public_key, Ed25519PublicKey), "Key must be Ed25519")
    raw = public_key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return hashlib.sha256(raw).hexdigest()


def _validate_body(body: dict) -> None:
    _fields(body, _BODY_FIELDS, "body")
    _require(type(body["protocol_version"]) is str, "protocol_version must be a string")
    _require(body["protocol_version"] == PROTOCOL_VERSION, "Unsupported protocol version", "UNSUPPORTED_VERSION")
    for name, expected in (("hash_algorithm", "sha256"), ("signature_algorithm", "ed25519"), ("evidence", "HASH_RECEIPT")):
        _require(type(body[name]) is str and body[name] == expected, f"Invalid {name}")
    _matches(body["issuer_id"], _ISSUER, "issuer_id")
    _matches(body["key_id"], _HEX64, "key_id")
    _matches(body["pair_id"], _HEX64, "pair_id")
    _require(type(body["environment"]) is str and body["environment"] in ENVIRONMENTS, "Invalid environment")
    _require(type(body["receipt_id"]) is str, "receipt_id must be a string")
    try:
        receipt_uuid = UUID(body["receipt_id"])
    except (ValueError, AttributeError) as exc:
        raise CoreValidationError("Invalid receipt_id") from exc
    _require(receipt_uuid.version == 4 and str(receipt_uuid) == body["receipt_id"], "receipt_id must be canonical UUIDv4")
    _matches(body["received_at"], _TIMESTAMP, "received_at")
    try:
        datetime.strptime(body["received_at"], "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError as exc:
        raise CoreValidationError("received_at must be a valid UTC date") from exc
    validate_pair(body["pair"])
    canonical_bytes(body)


def sign_receipt(pair: dict, private_key: Ed25519PrivateKey, *, issuer_id: str, environment: str, receipt_id: str, received_at: str) -> dict:
    """Sign a caller-supplied reception assertion, without consulting clock/files."""
    _require(isinstance(private_key, Ed25519PrivateKey), "Key must be Ed25519 private key")
    # Snapshot through the canonical encoding; the caller cannot mutate our pair.
    pair_copy = strict_json_loads(canonical_bytes(validate_pair(pair)))
    body = {
        "protocol_version": PROTOCOL_VERSION, "hash_algorithm": "sha256",
        "signature_algorithm": "ed25519", "issuer_id": issuer_id,
        "key_id": key_id(private_key.public_key()), "environment": environment,
        "receipt_id": receipt_id, "received_at": received_at,
        "evidence": "HASH_RECEIPT", "pair": pair_copy, "pair_id": derive_pair_id(pair_copy),
    }
    _validate_body(body)
    return {"body": body, "signature": private_key.sign(CERTIFICATE_DOMAIN + canonical_bytes(body)).hex()}


def _original_hashes(originals: dict | None, pair: dict) -> dict:
    if originals is None:
        return {}
    try:
        _require(type(originals) is dict and set(originals) <= {"par1", "par2"}, "Invalid originals object")
        result = {}
        for name, supplied in originals.items():
            profile = pair[name]["profile"]
            field = "text" if profile == TEXT_PROFILE else "base64"
            _fields(supplied, {field}, name)
            value = supplied[field]
            _require(type(value) is str, f"{field} must be str")
            if field == "base64":
                _require(value.isascii(), "Base64 must be ASCII")
                try:
                    decoded = base64.b64decode(value, validate=True)
                except (ValueError, binascii.Error) as exc:
                    raise CoreValidationError("Invalid standard base64") from exc
                _require(base64.b64encode(decoded).decode("ascii") == value, "Base64 must use canonical padding")
                value = decoded
            result[name] = hash_element(value, profile)["hash"]
        return result
    except CoreValidationError as exc:
        if exc.code == "UNSUPPORTED_UNICODE_VERSION":
            raise
        raise CoreValidationError(str(exc), "MALFORMED_ORIGINALS") from exc


def verify_receipt(certificate: dict, *, trusted_keys: dict, expected_environment: str, originals: dict | None = None, candidate_keys: dict | None = None, revoked_keys: set | None = None) -> dict:
    """Verify each guarantee separately, using only explicit local key material.

Malformed certificates return schema=FAIL. Malformed optional originals raise
CoreValidationError(code='MALFORMED_ORIGINALS') before any trust/key lookup.
"""
    _require(type(expected_environment) is str and expected_environment in ENVIRONMENTS, "Invalid expected_environment")
    result = {
        "status": "MALFORMED_CERTIFICATE", "schema": "NOT_CHECKED",
        "signature": "NOT_CHECKED", "issuer_trust": "UNKNOWN",
        "environment": "NOT_CHECKED", "pair_binding": "NOT_CHECKED",
        "content": "NOT_CHECKED", "content_checks": {"par1": "NOT_CHECKED", "par2": "NOT_CHECKED"},
        "errors": [],
    }
    try:
        _fields(certificate, {"body", "signature"}, "certificate")
        _validate_body(certificate["body"])
        _matches(certificate["signature"], _HEX128, "signature")
    except CoreValidationError as exc:
        result.update(status=exc.code if exc.code == "UNSUPPORTED_VERSION" else "MALFORMED_CERTIFICATE", schema="FAIL")
        result["errors"].append(result["status"])
        return result

    body = certificate["body"]
    hashes = _original_hashes(originals, body["pair"])
    result["schema"] = "PASS"
    errors = result["errors"]
    _require(type(trusted_keys) is dict, "trusted_keys must be a dict")
    _require(candidate_keys is None or type(candidate_keys) is dict, "candidate_keys must be a dict")
    _require(revoked_keys is None or type(revoked_keys) in (set, frozenset), "revoked_keys must be a set")
    trusted_key = trusted_keys.get((body["issuer_id"], body["environment"], body["key_id"]))
    public_key = trusted_key if trusted_key is not None else (candidate_keys or {}).get(body["key_id"])
    revoked = body["key_id"] in (revoked_keys or set())
    if revoked:
        result["issuer_trust"] = "REVOKED"
        errors.append("KEY_REVOKED")
    elif trusted_key is not None:
        result["issuer_trust"] = "TRUSTED"
    else:
        errors.append("UNTRUSTED_ISSUER")
    if public_key is None:
        errors.append("KEY_UNAVAILABLE")
    else:
        _require(isinstance(public_key, Ed25519PublicKey), "Verification key must be Ed25519")
        try:
            if key_id(public_key) != body["key_id"]:
                raise InvalidSignature
            public_key.verify(bytes.fromhex(certificate["signature"]), CERTIFICATE_DOMAIN + canonical_bytes(body))
            result["signature"] = "PASS"
        except InvalidSignature:
            result["signature"] = "FAIL"
            errors.append("INVALID_SIGNATURE")

    result["environment"] = "PASS" if body["environment"] == expected_environment else "FAIL"
    if result["environment"] == "FAIL":
        errors.append("ENVIRONMENT_MISMATCH")
    result["pair_binding"] = "PASS" if derive_pair_id(body["pair"]) == body["pair_id"] else "FAIL"
    if result["pair_binding"] == "FAIL":
        errors.append("INVALID_PAIR_BINDING")
    for name, actual in hashes.items():
        result["content_checks"][name] = "PASS" if actual == body["pair"][name]["hash"] else "FAIL"
    if "FAIL" in result["content_checks"].values():
        result["content"] = "FAIL"
        errors.append("CONTENT_MISMATCH")
    elif all(value == "PASS" for value in result["content_checks"].values()):
        result["content"] = "PASS"
    result["errors"] = [code for code in _FAILURE_PRIORITY if code in errors]
    result["status"] = result["errors"][0] if result["errors"] else ("VERIFIED_CONTENT" if result["content"] == "PASS" else "VERIFIED_RECEIPT")
    return result


def verify_legacy_v1_2(document: dict, public_key: Ed25519PublicKey, *, prompt_text: str | None = None, response_text: str | None = None) -> dict:
    """Read only the explicitly identified v1.2 issuer six-field/hex format.

Key material and optional originals are supplied by the caller. This limited
reader never authenticates the unsigned issuer identity or fetches a URL. It
uses the issuer's verbatim model string, including the historic delimiter
ambiguity; it does not guess other historical formats or regenerate signatures.
    """
    result = {
        "status": "LEGACY_LIMITED", "legacy_format": "IAHASH-1.2/issuer-six-field-hex",
        "schema": "NOT_CHECKED", "signature": "NOT_CHECKED", "issuer_trust": "UNKNOWN",
        "pair_binding": "NOT_CHECKED", "content": "NOT_CHECKED", "identifier": "NOT_CHECKED",
        "content_checks": {"par1": "NOT_CHECKED", "par2": "NOT_CHECKED"}, "errors": [],
        "signed_fields": ["protocol_version", "prompt_id", "h_prompt", "h_response", "model", "timestamp"],
        "limitations": [
            "ISSUER_IDENTITY_UNSIGNED", "OTHER_METADATA_UNSIGNED", "DELIMITER_AMBIGUITY",
            "DECLARED_TIME_ONLY", "UNICODE_VERSION_AT_ISSUANCE_UNKNOWN",
            "ISSUER_FORMULA_WITHOUT_VERIFIER_MODEL_FALLBACK",
        ],
    }
    try:
        _require(type(document) is dict, "Legacy document must be an object")
        _require(document.get("protocol_version") == "IAHASH-1.2", "Unsupported explicit legacy format", "UNSUPPORTED_VERSION")
        _require("prompt_id" in document and (document["prompt_id"] is None or type(document["prompt_id"]) is str), "Invalid legacy prompt_id")
        for field in ("h_prompt", "h_response", "h_total"):
            _matches(document.get(field), _HEX64, field)
        _matches(document.get("signature"), _HEX128, "signature")
        for field in ("model", "timestamp"):
            _require(type(document.get(field)) is str, f"Invalid legacy {field}")
        preimage = "|".join([
            "IAHASH-1.2", document["prompt_id"] or "", document["h_prompt"],
            document["h_response"], document["model"], document["timestamp"],
        ])
        preimage_bytes = preimage.encode("utf-8")
    except (CoreValidationError, UnicodeError) as exc:
        code = exc.code if isinstance(exc, CoreValidationError) else "MALFORMED_CERTIFICATE"
        result.update(status=code, schema="FAIL")
        result["errors"].append(code)
        return result

    _require(isinstance(public_key, Ed25519PublicKey), "Verification key must be Ed25519")
    result["schema"] = "PASS"
    result["pair_binding"] = "PASS" if hashlib.sha256(preimage_bytes).hexdigest() == document["h_total"] else "FAIL"
    if result["pair_binding"] == "FAIL":
        result["errors"].append("INVALID_PAIR_BINDING")
    try:
        public_key.verify(bytes.fromhex(document["signature"]), document["h_total"].encode("utf-8"))
        result["signature"] = "PASS"
    except InvalidSignature:
        result["signature"] = "FAIL"
        result["errors"].append("INVALID_SIGNATURE")
    for name, text, field in (("par1", prompt_text, "h_prompt"), ("par2", response_text, "h_response")):
        if text is not None:
            result["content_checks"][name] = "PASS" if hashlib.sha256(_text_bytes(text)).hexdigest() == document[field] else "FAIL"
    if "FAIL" in result["content_checks"].values():
        result["content"] = "FAIL"
        result["errors"].append("CONTENT_MISMATCH")
    elif all(value == "PASS" for value in result["content_checks"].values()):
        result["content"] = "PASS"
    if "iah_id" in document:
        digest = hashlib.sha256(document["h_total"].encode("utf-8")).digest()
        number, encoded = int.from_bytes(digest, "big"), ""
        alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
        if number == 0:
            encoded = "1"  # Preserve the historical all-zero encoder edge case.
        else:
            while number:
                number, remainder = divmod(number, 58)
                encoded = alphabet[remainder] + encoded
            encoded = "1" * (len(digest) - len(digest.lstrip(b"\x00"))) + encoded
        result["identifier"] = "PASS" if document["iah_id"] == encoded[:16] else "FAIL"
        if result["identifier"] == "FAIL":
            result["errors"].append("LEGACY_IDENTIFIER_MISMATCH")
    return result


__all__ = [
    "PROTOCOL_VERSION", "TEXT_PROFILE", "BYTES_PROFILE", "UNICODE_VERSION",
    "CoreValidationError", "strict_json_loads", "canonical_bytes", "validate_pair",
    "hash_element", "make_pair", "derive_pair_id", "key_id", "sign_receipt", "verify_receipt",
    "verify_legacy_v1_2",
]
