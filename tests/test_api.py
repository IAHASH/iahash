from fastapi.testclient import TestClient


def create_client():
    from api.main import app

    return TestClient(app)


def test_health_endpoint(temp_keys, monkeypatch):
    monkeypatch.setenv("IAHASH_KEYS_DIR", str(temp_keys))
    client = create_client()
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_issue_and_verify_flow(temp_keys, monkeypatch):
    monkeypatch.setenv("IAHASH_KEYS_DIR", str(temp_keys))
    client = create_client()

    issue_resp = client.post(
        "/issue",
        json={
            "prompt_maestro": "Hola",
            "respuesta": "Mundo",
            "modelo": "api-model",
            "prompt_id": "P1",
            "subject_id": "S1",
        },
    )
    assert issue_resp.status_code == 200
    doc = issue_resp.json()
    assert doc["h_total"]

    verify_resp = client.post("/verify", json=doc)
    assert verify_resp.status_code == 200
    assert verify_resp.json()["valid"] is True

    pk_resp = client.get("/public-key")
    assert pk_resp.status_code == 200
    assert "PUBLIC KEY" in pk_resp.text


def test_master_prompts_listed(temp_keys, monkeypatch):
    monkeypatch.setenv("IAHASH_KEYS_DIR", str(temp_keys))
    client = create_client()
    resp = client.get("/master-prompts")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert any(item["id"] == "cv-honesto-v1" for item in data)
