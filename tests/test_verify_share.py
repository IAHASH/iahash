from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import iahash.extractors.chatgpt_share as chatgpt_share
from api.main import app

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "chatgpt_share_sample.html"


@pytest.fixture()
def share_html():
    return FIXTURE_PATH.read_text()


def create_client():
    return TestClient(app)


def test_verify_share_success(temp_keys, monkeypatch, share_html):
    monkeypatch.setenv("IAHASH_KEYS_DIR", str(temp_keys))

    def fake_download(url: str) -> str:
        assert url.startswith("https://chatgpt.com/share/")
        return share_html

    monkeypatch.setattr(chatgpt_share, "_download_html", fake_download)

    client = create_client()
    resp = client.post(
        "/api/verify/share",
        json={
            "share_url": "https://chatgpt.com/share/6935bbc0-3fc4-8001-b6fa-b57c687905a8"
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["error"] is None
    assert data["reason"] is None
    assert data["extracted_prompt"]
    assert data["extracted_answer"]
    assert data["provider"] == "chatgpt"
    assert data["model"] == "gpt-4o"
    assert data["conversation_url"].startswith("https://chatgpt.com/share/")


def test_verify_share_invalid_url(temp_keys):
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setenv("IAHASH_KEYS_DIR", str(temp_keys))
    client = create_client()

    resp = client.post(
        "/api/verify/share",
        json={"share_url": "https://example.com/share/bad"},
    )

    assert resp.status_code == 400
    data = resp.json()
    assert data["success"] is False
    assert data["reason"] == "INVALID_URL"
    monkeypatch.undo()


def test_verify_share_parsing_failure(temp_keys, monkeypatch):
    monkeypatch.setenv("IAHASH_KEYS_DIR", str(temp_keys))

    def fake_download(_url: str) -> str:
        return "<html></html>"

    monkeypatch.setattr(chatgpt_share, "_download_html", fake_download)

    client = create_client()
    resp = client.post(
        "/api/verify/share",
        json={
            "share_url": "https://chatgpt.com/share/6935bbc0-3fc4-8001-b6fa-b57c687905a8"
        },
    )

    assert resp.status_code == 400
    data = resp.json()
    assert data["success"] is False
    assert data["reason"] == "PARSING_FAILED"
