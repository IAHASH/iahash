import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(temp_keys, monkeypatch):
    monkeypatch.setenv("IAHASH_KEYS_DIR", str(temp_keys))
    import api.main as api_main

    importlib.reload(api_main)
    return TestClient(api_main.app)


def test_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_issue_and_verify_endpoints(client):
    payload = {
        "prompt_maestro": "Hola",
        "respuesta": "Mundo",
        "modelo": "gpt-test",
        "prompt_id": "demo",
    }
    issue_res = client.post("/api/issue", json=payload)
    assert issue_res.status_code == 200
    doc = issue_res.json()

    verify_res = client.post("/api/verify", json=doc)
    assert verify_res.status_code == 200
    data = verify_res.json()
    assert data["valid"] is True


def test_public_key_endpoint(client, temp_keys):
    res = client.get("/api/public-key")
    assert res.status_code == 200
    assert "BEGIN PUBLIC KEY" in res.text


def test_master_prompts_endpoint(client):
    res = client.get("/api/master-prompts")
    assert res.status_code == 200
    assert any(item["id"] == "cv-honesto-v1" for item in res.json())
