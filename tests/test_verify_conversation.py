from __future__ import annotations

import json

from fastapi.testclient import TestClient

import iahash.extractors.chatgpt_share as chatgpt_share


def create_client():
    from api.main import app

    return TestClient(app)


def build_share_html(prompt_text: str, response_text: str, model: str) -> str:
    next_data = {
        "props": {
            "pageProps": {
                "sharedConversation": {
                    "mapping": {
                        "u1": {
                            "message": {
                                "author": {"role": "user"},
                                "content": {"parts": [prompt_text]},
                            }
                        },
                        "a1": {
                            "message": {
                                "author": {"role": "assistant"},
                                "content": {"parts": [response_text]},
                            }
                        },
                    },
                    "modelSlug": model,
                }
            }
        }
    }
    return (
        '<html><script id="__NEXT_DATA__" type="application/json">'
        f"{json.dumps(next_data)}</script></html>"
    )


def test_verify_conversation_success(temp_keys, monkeypatch):
    monkeypatch.setenv("IAHASH_KEYS_DIR", str(temp_keys))
    client = create_client()

    html = build_share_html("Hola", "Mundo", "gpt-4o")
    monkeypatch.setattr(chatgpt_share, "fetch_share_html", lambda url: html)

    resp = client.post(
        "/api/verify/conversation",
        json={
            "prompt_text": "Hola",
            "response_text": "Mundo",
            "prompt_id": "P1",
            "model": "ignored",
            "conversation_url": "https://chatgpt.com/share/abc",
            "provider": "chatgpt",
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["model"] == "gpt-4o"
    assert data["provider"] == "chatgpt"


def test_verify_conversation_unreachable(temp_keys, monkeypatch):
    monkeypatch.setenv("IAHASH_KEYS_DIR", str(temp_keys))
    client = create_client()

    def _raise(_url):
        raise RuntimeError(chatgpt_share.ERROR_UNREACHABLE)

    monkeypatch.setattr(chatgpt_share, "fetch_share_html", _raise)

    resp = client.post(
        "/api/verify/conversation",
        json={
            "prompt_text": "Hola",
            "response_text": "Mundo",
            "prompt_id": "P1",
            "model": "ignored",
            "conversation_url": "https://chatgpt.com/share/unreachable",
            "provider": "chatgpt",
        },
    )

    assert resp.status_code == 400
    assert resp.json()["detail"] == "Conversation URL unreachable"


def test_verify_conversation_unsupported_format(temp_keys, monkeypatch):
    monkeypatch.setenv("IAHASH_KEYS_DIR", str(temp_keys))
    client = create_client()

    monkeypatch.setattr(chatgpt_share, "fetch_share_html", lambda url: "<html></html>")

    resp = client.post(
        "/api/verify/conversation",
        json={
            "prompt_text": "Hola",
            "response_text": "Mundo",
            "prompt_id": "P1",
            "model": "ignored",
            "conversation_url": "https://chatgpt.com/share/unsupported",
            "provider": "chatgpt",
        },
    )

    assert resp.status_code == 400
    assert resp.json()["detail"] == "Unsupported conversation format"
