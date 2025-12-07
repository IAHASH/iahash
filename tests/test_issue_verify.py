from __future__ import annotations

import httpx
import pytest

from iahash.issuer import issue_pair
from iahash.verifier import VerificationStatus, verify_document


@pytest.fixture(autouse=True)
def disable_db_writes(monkeypatch):
    monkeypatch.setattr("iahash.issuer.store_iah_document", lambda document: None)


def test_issue_and_verify_roundtrip(monkeypatch, temp_keys):
    public_key_bytes = (temp_keys / "issuer_ed25519.pub").read_bytes()

    def fake_get(url, timeout=None):
        return httpx.Response(200, request=httpx.Request("GET", url), content=public_key_bytes)

    monkeypatch.setattr("iahash.verifier.httpx.get", fake_get)

    doc = issue_pair(
        prompt_text="Hola IA",
        response_text="Hola humano",
        prompt_id="demo",
        model="gpt-test",
        issuer_pk_url="http://issuer.test/pubkey.pem",
    )

    result = verify_document(doc)

    assert result["valid"] is True
    assert result["status"] == VerificationStatus.VALID


def test_verifier_detects_tampering(monkeypatch, temp_keys):
    public_key_bytes = (temp_keys / "issuer_ed25519.pub").read_bytes()

    def fake_get(url, timeout=None):
        return httpx.Response(200, request=httpx.Request("GET", url), content=public_key_bytes)

    monkeypatch.setattr("iahash.verifier.httpx.get", fake_get)

    doc = issue_pair(
        prompt_text="Original",
        response_text="Contenido",
        model="gpt-x",
        issuer_pk_url="http://issuer.test/pubkey.pem",
        store_raw=True,
    )

    tampered = doc.copy()
    tampered["raw_prompt_text"] = "Original modificado"

    result = verify_document(tampered)

    assert result["valid"] is False
    assert result["status"] == VerificationStatus.PROMPT_MISMATCH
    assert any("Prompt" in error or "prompt" in error for error in result["errors"])
