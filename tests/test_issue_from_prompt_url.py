from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from api.main import app
from iahash.db import create_prompt


@pytest.fixture()
def prompt_record(monkeypatch):
    monkeypatch.setenv("IAHASH_PROMPT_HMAC_KEY", "test-key")
    slug = f"prompt-{uuid.uuid4()}"
    prompt_id = create_prompt(slug=slug, title="Prompt", full_prompt="Hola IA")
    return prompt_id


def test_issue_from_prompt_url_issues_document(monkeypatch, temp_keys, prompt_record):
    monkeypatch.setenv("IAHASH_KEYS_DIR", str(temp_keys))

    share_url = "https://chatgpt.com/share/a1b2c3d4-1234"

    def fake_extract(url: str):
        assert url == share_url
        return {
            "prompt_text": "Hola IA",
            "response_text": "Respuesta IA",
            "model": "gpt-4o",
            "provider": "chatgpt",
            "conversation_url": url,
        }

    monkeypatch.setattr("api.main.extract_chatgpt_share", fake_extract)

    client = TestClient(app)
    resp = client.post(
        "/api/issue/from_prompt_url",
        json={
            "prompt_id": str(prompt_record),
            "provider": "chatgpt",
            "share_url": share_url,
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ISSUED"
    assert data["error"] is None

    document = data.get("document") or {}
    assert document.get("conversation_url") == share_url
    assert document.get("provider") == "chatgpt"
    assert document.get("prompt_id") == str(prompt_record)
    assert document.get("model") == "gpt-4o"
    assert document.get("h_prompt")
    assert document.get("h_response")


def test_issue_from_prompt_url_invalid_url(monkeypatch, temp_keys, prompt_record):
    monkeypatch.setenv("IAHASH_KEYS_DIR", str(temp_keys))

    client = TestClient(app)
    resp = client.post(
        "/api/issue/from_prompt_url",
        json={"prompt_id": str(prompt_record), "provider": "chatgpt", "share_url": "invalid"},
    )

    assert resp.status_code == 400
    data = resp.json()
    assert data["status"] == "ERROR"
    assert data["document"] is None
    assert data["error"]["code"] == "INVALID_URL"
