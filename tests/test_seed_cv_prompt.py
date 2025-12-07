from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app
from iahash import db
from iahash.db import ensure_db_initialized, get_prompt_by_slug, list_prompts


def test_cv_seed_is_available(monkeypatch, tmp_path, temp_keys):
    monkeypatch.setenv("IAHASH_PROMPT_HMAC_KEY", "seed-key")
    monkeypatch.setenv("IAHASH_KEYS_DIR", str(temp_keys))

    monkeypatch.setattr(db, "DB_PATH", tmp_path / "iahash.db")
    ensure_db_initialized()

    prompts = list_prompts(visibility="public")
    cv_prompt = next(p for p in prompts if p["slug"] == "cv")
    assert cv_prompt["h_public"] == "28321723bccc8727a57bc6997bd6889524c3f862cc7956fc652ba80ce8252e91bd"

    prompt_record = get_prompt_by_slug("cv")
    share_url = "https://chatgpt.com/share/6935bbc0-3fc4-8001-b6fa-b57c687905a8"

    def fake_extract(url: str):
        assert url == share_url
        return {
            "prompt_text": prompt_record["full_prompt"],
            "response_text": "Respuesta IA",
            "model": "gpt-4o",
            "provider": "chatgpt",
            "conversation_url": url,
        }

    monkeypatch.setattr("api.main.extract_chatgpt_share", fake_extract)

    client = TestClient(app)
    resp = client.post(
        "/api/issue/from_prompt_url",
        json={"prompt_id": "cv", "provider": "chatgpt", "share_url": share_url},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ISSUED"
    document = data["document"]
    assert document["prompt_public_hash"] == cv_prompt["h_public"]
    assert document["prompt_id"] == str(cv_prompt["id"])
