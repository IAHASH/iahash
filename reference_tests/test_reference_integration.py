"""Local in-process end-to-end checks; no external service or production data."""
from pathlib import Path
from contextlib import closing
import sqlite3

import httpx
from fastapi.testclient import TestClient
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from iahash_core import make_pair, key_id, verify_receipt
from iahash_server.app import create_app
from iahash_server.__main__ import backup_database, init_key
from iahash_client import Client


def test_lost_response_retry_restart_and_backup(tmp_path):
    private_key = Ed25519PrivateKey.generate()
    trust = {("integration.lab", "LAB", key_id(private_key.public_key())): private_key.public_key()}
    token = "synthetic-integration-token-32-characters"
    db = tmp_path / "registry.sqlite"
    app = create_app(db_path=db, private_key=private_key,
                     issuer_id="integration.lab", environment="LAB", api_token=token)
    pair = make_pair("Cafe\u0301\r\n", "Réponse\n")
    requests = []
    with TestClient(app) as server:
        def transport(request):
            requests.append(request.headers.get("Idempotency-Key"))
            response = server.request(request.method, request.url.path,
                                      headers=dict(request.headers), content=request.content)
            if len(requests) == 1:
                assert response.status_code == 201
                raise httpx.ReadTimeout("Response lost after durable commit", request=request)
            return httpx.Response(response.status_code, content=response.content,
                                  headers=response.headers, request=request)
        with Client(base_url="https://issuer.test", queue_path=tmp_path / "queue.sqlite",
                    api_token=token, trusted_keys=trust, expected_environment="LAB",
                    transport=httpx.MockTransport(transport), sleep=lambda _: None) as client:
            idem = client.enqueue(pair)
            result = client.send(idem)
            assert result["status"] == "CONFIRMED", result
            certificate = result["certificate"]
        assert requests == [idem, idem]
        checked = verify_receipt(certificate, trusted_keys=trust, expected_environment="LAB",
                                 originals={"par1": {"text": "Café"}, "par2": {"text": "Réponse"}})
        assert checked["status"] == "VERIFIED_CONTENT"
        with closing(sqlite3.connect(db)) as conn:
            assert conn.execute("SELECT COUNT(*) FROM receipts").fetchone() == (1,)
    backup_database(db, tmp_path / "snapshot.sqlite")
    backup_database(tmp_path / "snapshot.sqlite", tmp_path / "restored.sqlite")
    restored = create_app(db_path=tmp_path / "restored.sqlite", private_key=private_key,
                          issuer_id="integration.lab", environment="LAB", api_token=token)
    with TestClient(restored) as server:
        response = server.post("/api/pair-v1/receipts", json=pair,
                               headers={"Authorization": f"Bearer {token}", "Idempotency-Key": idem})
        assert response.status_code == 200
        assert response.json() == certificate
    with Client(base_url="https://issuer.test", queue_path=tmp_path / "queue.sqlite",
                api_token=token, trusted_keys=trust, expected_environment="LAB",
                transport=httpx.MockTransport(lambda _: (_ for _ in ()).throw(AssertionError("No replay expected")))) as client:
        assert client.send(idem)["status"] == "CONFIRMED"


def test_explicit_key_operations_never_rotate(tmp_path):
    private = tmp_path / "keys" / "issuer.private"
    public = tmp_path / "keys" / "issuer.pub"
    init_key(private, public)
    original = private.read_bytes()
    public_before = public.read_bytes()
    public.unlink()  # A synthetic test fixture, never an operational key.
    init_key(private, public)
    assert private.read_bytes() == original
    assert public.read_bytes() == public_before
    init_key(private, public)
    assert private.read_bytes() == original
