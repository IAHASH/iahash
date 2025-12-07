from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient

from api.main import app
from iahash.extractors.chatgpt_share import (
    extract_payload_from_chatgpt_share,
    extract_prompt_and_response_from_chatgpt_share,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "chatgpt_share_sample.html"


def load_fixture_data():
    html = FIXTURE_PATH.read_text()
    soup = BeautifulSoup(html, "html.parser")
    data = json.loads(soup.find("script", id="__NEXT_DATA__").string)
    return html, data


def test_extract_prompt_and_response_from_chatgpt_share():
    _, data = load_fixture_data()
    prompt_text, response_text = extract_prompt_and_response_from_chatgpt_share(data)
    payload = extract_payload_from_chatgpt_share(data)

    assert prompt_text == "Hola, ¿puedes resumir mi perfil?"
    assert response_text == "Aquí tienes un resumen de tu perfil profesional."
    assert payload["model"] == "gpt-4o"


def test_issue_from_share_endpoint(temp_keys, monkeypatch):
    monkeypatch.setenv("IAHASH_KEYS_DIR", str(temp_keys))
    html, _ = load_fixture_data()

    class DummyResponse:
        def __init__(self, text: str, status_code: int = 200):
            self.text = text
            self.status_code = status_code

    class DummyAsyncClient:
        def __init__(self, *args, **kwargs):
            self._response = DummyResponse(html)

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url):
            return self._response

    monkeypatch.setattr(httpx, "AsyncClient", DummyAsyncClient)

    client = TestClient(app)
    resp = client.post(
        "/api/issue-from-share",
        json={
            "share_url": "https://chatgpt.com/share/abc123",
            "model": "chatgpt",
            "prompt_id": "P-123",
            "subject_id": "S-789",
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["model"] == "gpt-4o"
    assert data.get("conversation_url") == "https://chatgpt.com/share/abc123"
    assert data.get("prompt_id") == "P-123"
    assert data.get("h_prompt")
    assert data.get("h_response")
