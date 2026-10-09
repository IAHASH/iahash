"""Isolated tests: synthetic hashes, temporary storage, in-memory identities."""
from concurrent.futures import ThreadPoolExecutor
import base64
import json
import sqlite3
import uuid

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
import pytest

from iahash_core import make_pair
from iahash_server.app import PREFIX, create_app

TOKEN = "synthetic-lab-test-token"
HEADERS = {"Authorization": "Bearer " + TOKEN, "Idempotency-Key": "a" * 64}


@pytest.fixture
def service(tmp_path):
    key = Ed25519PrivateKey.generate()
    path = tmp_path / "receipts.db"
    options = dict(db_path=path, private_key=key, issuer_id="test.operator",
                   environment="LAB", api_token=TOKEN)
    app = create_app(**options)
    return app, TestClient(app), options


def issue(client, pair=None, headers=None):
    return client.post(PREFIX + "/receipts", json=pair or make_pair("one", "two"),
                       headers=headers or HEADERS)


def test_issue_replay_lookup_and_restart_preserve_exact_bytes(service):
    app, client, options = service
    first = issue(client)
    assert first.status_code == 201
    second = issue(client)
    assert second.status_code == 200
    assert first.content == second.content
    certificate = first.json()
    rid = certificate["body"]["receipt_id"]
    assert client.get(PREFIX + "/receipts/" + rid, headers=HEADERS).content == first.content
    restarted = TestClient(create_app(**options))
    assert issue(restarted).content == first.content
    connection = sqlite3.connect(options["db_path"])
    try:
        assert connection.execute("SELECT COUNT(*) FROM receipts").fetchone()[0] == 1
        assert connection.execute("SELECT certificate FROM receipts").fetchone()[0] == first.content
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 1
        assert connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    finally:
        connection.close()


def test_same_key_different_pair_conflicts_without_overwrite(service):
    _, client, _ = service
    original = issue(client)
    conflict = issue(client, make_pair("one", "changed"))
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"
    assert issue(client).content == original.content


def test_concurrent_same_key_commits_single_receipt(service):
    _, client, options = service
    with ThreadPoolExecutor(max_workers=4) as executor:
        responses = list(executor.map(lambda _: issue(client), range(4)))
    assert sorted(r.status_code for r in responses) == [200, 200, 200, 201]
    assert len({r.content for r in responses}) == 1
    connection = sqlite3.connect(options["db_path"])
    try:
        assert connection.execute("SELECT COUNT(*) FROM receipts").fetchone()[0] == 1
    finally:
        connection.close()


@pytest.mark.parametrize("field,value", [("issuer_id", "other.operator"),
                                         ("environment", "STAGING"),
                                         ("private_key", None)])
def test_restart_identity_mismatch_fails_without_erasing(service, field, value):
    _, client, options = service
    original = issue(client).content
    changed = {**options, field: value or Ed25519PrivateKey.generate()}
    with pytest.raises(RuntimeError, match="identity"):
        create_app(**changed)
    assert issue(TestClient(create_app(**options))).content == original


@pytest.mark.parametrize("kind", ["empty", "foreign", "unknown-version", "corrupt"])
def test_unknown_storage_fails_closed_without_deletion(tmp_path, kind):
    path = tmp_path / "unknown.db"
    if kind == "corrupt":
        path.write_bytes(b"existing evidence is not a SQLite file")
    elif kind == "empty":
        path.write_bytes(b"")
    else:
        connection = sqlite3.connect(path)
        connection.execute("CREATE TABLE evidence (value TEXT)")
        connection.execute("INSERT INTO evidence VALUES ('preserve')")
        if kind == "unknown-version":
            connection.execute("PRAGMA user_version=99")
        connection.commit()
        connection.close()
    original = path.read_bytes()
    with pytest.raises((RuntimeError, sqlite3.Error)):
        create_app(db_path=path, private_key=Ed25519PrivateKey.generate(),
                   issuer_id="test.operator", environment="LAB", api_token=TOKEN)
    assert path.exists() and path.read_bytes() == original


def test_auth_public_health_and_issuer(service):
    _, client, options = service
    assert client.get(PREFIX + "/health").json() == {"status": "ok"}
    assert client.get(PREFIX + "/ready").status_code == 200
    assert client.get(PREFIX + "/issuer").status_code == 401
    assert client.get(PREFIX + "/issuer", headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert client.post(PREFIX + "/verify", json={}, headers={}).status_code == 401
    issuer = client.get(PREFIX + "/issuer", headers=HEADERS).json()
    assert issuer["issuer_id"] == options["issuer_id"]
    assert issuer["environment"] == "LAB" and "PUBLIC KEY" in issuer["pem"]
    assert set(issuer) == {"issuer_id", "environment", "key_id", "pem"}


def test_verify_receipt_content_and_wrong_content(service):
    _, client, options = service
    certificate = issue(client).json()
    verify_url = PREFIX + "/verify"
    assert client.post(verify_url, json={"certificate": certificate}, headers=HEADERS).json()["status"] == "VERIFIED_RECEIPT"
    good = client.post(verify_url, json={"certificate": certificate, "originals": {
        "par1": {"text": "one"}, "par2": {"text": "two"}}}, headers=HEADERS)
    assert good.status_code == 200 and good.json()["status"] == "VERIFIED_CONTENT"
    wrong = client.post(verify_url, json={"certificate": certificate, "originals": {
        "par1": {"text": "wrong"}}}, headers=HEADERS)
    assert wrong.status_code == 200 and wrong.json()["status"] == "CONTENT_MISMATCH"
    certificate["body"]["issuer_id"] = "untrusted"
    negative = client.post(verify_url, json={"certificate": certificate}, headers=HEADERS)
    assert negative.status_code == 200 and negative.json()["status"] not in {"VERIFIED_RECEIPT", "VERIFIED_CONTENT"}
    connection = sqlite3.connect(options["db_path"])
    try:
        assert connection.execute("SELECT COUNT(*) FROM receipts").fetchone()[0] == 1
        assert b"wrong" not in connection.execute("SELECT certificate FROM receipts").fetchone()[0]
    finally:
        connection.close()


def test_strict_json_schema_media_and_size_errors(service):
    _, client, _ = service
    url = PREFIX + "/receipts"
    json_headers = {**HEADERS, "Content-Type": "application/json"}
    for invalid in [b'{"x":1,"x":2}', b'{', b'\xff']:
        response = client.post(url, content=invalid, headers=json_headers)
        assert response.status_code == 400
        assert set(response.json()) == {"error"}
    assert client.post(url, content=b"{}", headers=HEADERS).status_code == 422
    assert client.post(url, content=b"x" * (16 * 1024 + 1), headers=json_headers).status_code == 413
    assert client.post(url, json={**make_pair("one", "two"), "extra": "no"}, headers=HEADERS).status_code == 422
    assert issue(client, headers={"Authorization": "Bearer " + TOKEN}).status_code == 422
    certificate = issue(client).json()
    assert client.post(PREFIX + "/verify", json={"certificate": certificate, "originals": {
        "par1": {"base64": "%%%"}}}, headers=HEADERS).status_code == 422
    assert client.post(PREFIX + "/verify", json={"certificate": certificate, "extra": 1}, headers=HEADERS).status_code == 422
    assert client.post(PREFIX + "/verify", content=b"x" * (3 * 1024 * 1024 + 1), headers=json_headers).status_code == 413


def test_chunked_body_limit_before_parsing(service):
    _, client, _ = service
    response = client.post(PREFIX + "/receipts", content=iter([b"x" * 8192] * 3),
                           headers={**HEADERS, "Content-Type": "application/json"})
    assert response.status_code == 413


def test_rate_and_write_limits_retry_after(service):
    app, client, _ = service
    for _ in range(60):
        assert client.get(PREFIX + "/issuer", headers=HEADERS).status_code == 200
    limited = client.get(PREFIX + "/issuer", headers=HEADERS)
    assert limited.status_code == 429 and int(limited.headers["Retry-After"]) > 0
    assert client.get(PREFIX + "/health").status_code == 200
    app.state.rate_events.clear()
    for _ in range(4):
        assert app.state.write_slots.acquire(blocking=False)
    try:
        response = issue(client)
        assert response.status_code == 429 and response.headers["Retry-After"] == "1"
    finally:
        for _ in range(4):
            app.state.write_slots.release()


def test_missing_database_readiness_does_not_recreate(service):
    _, client, options = service
    options["db_path"].unlink()
    assert client.get(PREFIX + "/ready").status_code == 503
    assert not options["db_path"].exists()


def test_receipt_id_validation_not_found(service):
    _, client, _ = service
    assert client.get(PREFIX + "/receipts/not-a-uuid", headers=HEADERS).status_code == 422
    assert client.get(PREFIX + "/receipts/" + str(uuid.uuid4()), headers=HEADERS).status_code == 404


def test_identity_tampering_fails_readiness_and_writes(service):
    _, client, options = service
    connection = sqlite3.connect(options["db_path"])
    connection.execute("UPDATE identity SET value='other.operator' WHERE name='issuer_id'")
    connection.commit()
    connection.close()
    assert client.get(PREFIX + "/ready").status_code == 503
    assert issue(client).status_code == 503


@pytest.mark.parametrize("binary", [False, True])
def test_individual_original_limit_even_below_total_body_limit(service, binary):
    _, client, _ = service
    pair = make_pair(b"one", b"two", profile1="bytes-v1", profile2="bytes-v1") if binary else make_pair("one", "two")
    certificate = issue(client, pair).json()
    original = {"base64": base64.b64encode(b"x" * (1024 * 1024 + 1)).decode("ascii")} if binary else {"text": "x" * (1024 * 1024 + 1)}
    response = client.post(PREFIX + "/verify", json={"certificate": certificate, "originals": {
        "par1": original}}, headers=HEADERS)
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "ORIGINAL_TOO_LARGE"


def test_malformed_certificate_and_route_errors_have_error_envelope(service):
    _, client, _ = service
    malformed = client.post(PREFIX + "/verify", json={"certificate": {}}, headers=HEADERS)
    assert malformed.status_code == 422 and set(malformed.json()) == {"error"}
    missing = client.get(PREFIX + "/missing", headers=HEADERS)
    assert missing.status_code == 404 and set(missing.json()) == {"error"}
    method = client.delete(PREFIX + "/issuer", headers=HEADERS)
    assert method.status_code == 405 and set(method.json()) == {"error"}


@pytest.mark.parametrize("binary", [False, True])
def test_original_profile_mismatch_is_422(service, binary):
    _, client, _ = service
    pair = make_pair(b"one", b"two", profile1="bytes-v1", profile2="bytes-v1") if binary else make_pair("one", "two")
    certificate = issue(client, pair).json()
    incompatible = {"text": "one"} if binary else {"base64": "b25l"}
    response = client.post(PREFIX + "/verify", json={"certificate": certificate,
        "originals": {"par1": incompatible}}, headers=HEADERS)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "MALFORMED_ORIGINALS"


def test_unexpected_error_sanitized_and_transaction_rolled_back(service, monkeypatch):
    app, _, options = service
    import iahash_server.app as server_module

    def broken_signer(*args, **kwargs):
        raise ValueError("sensitive internal diagnostic")

    monkeypatch.setattr(server_module, "sign_receipt", broken_signer)
    client = TestClient(app, raise_server_exceptions=False)
    response = issue(client)
    assert response.status_code == 500
    assert response.json() == {"error": {"code": "INTERNAL_ERROR", "message": "Receipt service error"}}
    connection = sqlite3.connect(options["db_path"])
    try:
        assert connection.execute("SELECT COUNT(*) FROM receipts").fetchone()[0] == 0
    finally:
        connection.close()
