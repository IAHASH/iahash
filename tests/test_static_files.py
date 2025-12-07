from fastapi.testclient import TestClient


def create_client() -> TestClient:
    from api.main import app

    return TestClient(app)


def test_static_assets_served():
    client = create_client()

    css_resp = client.get("/static/styles.css")
    assert css_resp.status_code == 200
    assert "body" in css_resp.text

    logo_resp = client.get("/static/logo.png")
    assert logo_resp.status_code == 200
    assert logo_resp.headers.get("content-type", "").startswith("image/")
