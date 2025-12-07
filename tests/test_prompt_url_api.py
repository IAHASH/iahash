import importlib

import pytest
from fastapi.testclient import TestClient
from iahash.chatgpt import ChatGPTShare, ChatGPTShareError


@pytest.fixture
def client(temp_keys, monkeypatch):
    monkeypatch.setenv("IAHASH_KEYS_DIR", str(temp_keys))

    import api.main as api_main

    def fake_fetch(_url: str):
        return ChatGPTShare(prompt="Hola", response="Respuesta", model="gpt-4o", conversation_id="conv-123")

    importlib.reload(api_main)
    monkeypatch.setattr(api_main, "fetch_chatgpt_share", fake_fetch)

    return TestClient(api_main.app)


def test_verify_prompt_url_success(client):
    payload = {
        "prompt_id": "cv-honesto-v1",
        "provider": "chatgpt",
        "share_url": "https://chatgpt.com/share/abc",
    }

    res = client.post("/api/verify/prompt_url", json=payload)
    assert res.status_code == 200

    data = res.json()
    assert data["valid"] is True
    doc = data["document"]
    assert doc["prompt_maestro"] == "Hola"
    assert doc["respuesta"] == "Respuesta"
    assert doc["prompt_id"] == "cv-honesto-v1"


def test_verify_prompt_url_bad_provider(client):
    res = client.post(
        "/api/verify/prompt_url",
        json={"prompt_id": "cv", "provider": "bing", "share_url": "https://chatgpt.com/share/x"},
    )
    assert res.status_code == 400


def test_verify_prompt_url_fetch_error(temp_keys, monkeypatch):
    monkeypatch.setenv("IAHASH_KEYS_DIR", str(temp_keys))

    import api.main as api_main

    def fake_fetch(_url: str):
        raise ChatGPTShareError("fallo al leer share")

    importlib.reload(api_main)
    monkeypatch.setattr(api_main, "fetch_chatgpt_share", fake_fetch)
    test_client = TestClient(api_main.app)

    res = test_client.post(
        "/api/verify/prompt_url",
        json={"prompt_id": "cv", "provider": "chatgpt", "share_url": "https://chatgpt.com/share/x"},
    )
    assert res.status_code == 422
