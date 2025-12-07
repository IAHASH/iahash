from __future__ import annotations

import httpx
import pytest

from iahash.issuer import issue_pair
from iahash.verifier import VerificationStatus, verify_document


@pytest.fixture(autouse=True)
def disable_db_writes(monkeypatch):
    monkeypatch.setattr("iahash.issuer.store_iah_document", lambda document: None)


@pytest.fixture()
def public_key_bytes(temp_keys) -> bytes:  # type: ignore[override]
    return (temp_keys / "issuer_ed25519.pub").read_bytes()


def test_verifier_accepts_valid_document(monkeypatch, public_key_bytes):
    call_counter = {"count": 0}

    def fake_get(url, timeout=None):  # pragma: no cover - signature defined for monkeypatch
        call_counter["count"] += 1
        return httpx.Response(200, request=httpx.Request("GET", url), content=public_key_bytes)

    monkeypatch.setattr("iahash.verifier.httpx.get", fake_get)

    doc = issue_pair(
        prompt_text="Pregunta?",
        response_text="Respuesta",
        model="gpt-x",
        issuer_pk_url="http://issuer.test/pubkey.pem",
        store_raw=True,
    )

    result = verify_document(doc, use_cache=True)

    assert result["valid"] is True
    assert result["status"] == VerificationStatus.VALID
    assert call_counter["count"] == 1


def test_verifier_handles_missing_issuer_pk_url(monkeypatch, public_key_bytes):
    doc = issue_pair(
        prompt_text="Pregunta?",
        response_text="Respuesta",
        model="gpt-x",
        issuer_pk_url="http://issuer.test/pubkey.pem",
    )
    doc.pop("issuer_pk_url")

    result = verify_document(doc)

    assert result["valid"] is False
    assert result["status"] == VerificationStatus.UNREACHABLE_SOURCE
    assert "issuer_pk_url" in result["errors"][0]


def test_verifier_reports_invalid_url(monkeypatch, public_key_bytes):
    def fake_get(url, timeout=None):
        raise httpx.InvalidURL("bad url")

    monkeypatch.setattr("iahash.verifier.httpx.get", fake_get)

    doc = issue_pair(
        prompt_text="Pregunta?",
        response_text="Respuesta",
        model="gpt-x",
        issuer_pk_url="http://issuer.test/pubkey.pem",
    )

    result = verify_document(doc)

    assert result["valid"] is False
    assert result["status"] == VerificationStatus.UNREACHABLE_SOURCE
    assert "bad url" in result["errors"][0]


def test_verifier_reports_timeout(monkeypatch, public_key_bytes):
    def fake_get(url, timeout=None):
        raise httpx.ReadTimeout("timed out")

    monkeypatch.setattr("iahash.verifier.httpx.get", fake_get)

    doc = issue_pair(
        prompt_text="Pregunta?",
        response_text="Respuesta",
        model="gpt-x",
        issuer_pk_url="http://issuer.test/pubkey.pem",
    )

    result = verify_document(doc, timeout=0.1)

    assert result["valid"] is False
    assert result["status"] == VerificationStatus.UNREACHABLE_SOURCE
    assert "Timeout" in result["errors"][0]


def test_verifier_reuses_cache(monkeypatch, public_key_bytes):
    call_counter = {"count": 0}

    def fake_get(url, timeout=None):
        call_counter["count"] += 1
        return httpx.Response(200, request=httpx.Request("GET", url), content=public_key_bytes)

    monkeypatch.setattr("iahash.verifier.httpx.get", fake_get)

    key_cache = {}
    doc = issue_pair(
        prompt_text="Pregunta?",
        response_text="Respuesta",
        model="gpt-x",
        issuer_pk_url="http://issuer.test/pubkey.pem",
    )

    first = verify_document(doc, use_cache=True, key_cache=key_cache)
    second = verify_document(doc, use_cache=True, key_cache=key_cache)

    assert call_counter["count"] == 1
    assert first["valid"] is True
    assert second["valid"] is True
