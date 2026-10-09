"""Synthetic, offline checks for the durable reference delivery client."""

import json
from pathlib import Path
import sqlite3
from uuid import uuid4

import httpx
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from iahash_client import Client, QueueError
from iahash_core import (
    canonical_bytes, key_id, make_pair, sign_receipt, strict_json_loads,
)


@pytest.fixture
def identity():
    private = Ed25519PrivateKey.generate()
    public = private.public_key()
    return private, {("lab-issuer", "LAB", key_id(public)): public}


@pytest.fixture
def pair():
    return make_pair("Synthetic first element", b"Synthetic second element", profile2="bytes-v1")


def certificate(pair, private, *, environment="LAB", issuer="lab-issuer"):
    return sign_receipt(
        pair, private, issuer_id=issuer, environment=environment,
        receipt_id=str(uuid4()), received_at="2026-10-10T10:00:00.000000Z",
    )


def client(tmp_path, identity, handler, **overrides):
    options = {
        "base_url": "https://issuer.test",
        "queue_path": tmp_path / "queue.sqlite3",
        "api_token": "synthetic-lab-token",
        "trusted_keys": identity[1],
        "expected_environment": "LAB",
        "transport": httpx.MockTransport(handler),
        "sleep": lambda _: None,
    }
    options.update(overrides)
    return Client(**options)


def test_durable_before_send_and_exact_confirmation(tmp_path, identity, pair):
    seen = []
    # Signature verification canonicalizes the body; storage still retains the
    # exact received envelope bytes, including insignificant JSON whitespace.
    expected = json.dumps(certificate(pair, identity[0]), indent=2).encode("ascii")

    def handle(request):
        assert str(request.url) == "https://issuer.test/api/pair-v1/receipts"
        assert request.headers["Authorization"] == "Bearer synthetic-lab-token"
        key = request.headers["Idempotency-Key"]
        with sqlite3.connect(tmp_path / "queue.sqlite3") as conn:
            row = conn.execute(
                "SELECT pair,status,attempts FROM deliveries WHERE idempotency_key=?", (key,)
            ).fetchone()
        assert row == (canonical_bytes(pair), "SENDING", 1)
        seen.append(key)
        return httpx.Response(201, content=expected)

    with client(tmp_path, identity, handle) as delivery:
        key = delivery.enqueue(pair)
        assert len(key) == 64
        assert not seen
        assert delivery.get(key)["status"] == "PENDING"
        result = delivery.send(key)
        assert result["status"] == "CONFIRMED"
        assert result["certificate"] == strict_json_loads(expected)
        assert delivery.send(key) == result
        assert delivery.resume_pending() == []
        assert seen == [key]
    with sqlite3.connect(tmp_path / "queue.sqlite3") as conn:
        assert conn.execute("SELECT certificate FROM deliveries").fetchone()[0] == expected


def test_only_hashes_are_persisted(tmp_path, identity):
    original = "private synthetic source should never be persisted 9bd20ce3"
    p = make_pair(original, original)
    with client(tmp_path, identity, lambda _: pytest.fail("enqueue must not send")) as delivery:
        delivery.enqueue(p)
    with sqlite3.connect(tmp_path / "queue.sqlite3") as conn:
        rows = list(conn.execute("SELECT * FROM deliveries")) + list(conn.execute("SELECT * FROM metadata"))
    assert original not in repr(rows)
    assert "synthetic-lab-token" not in repr(rows)
    assert original.encode() not in (tmp_path / "queue.sqlite3").read_bytes()


def test_restart_recovers_sending_same_key_and_preserves_confirmed(tmp_path, identity, pair):
    expected = certificate(pair, identity[0])
    sent_keys = []

    def handle(request):
        sent_keys.append(request.headers["Idempotency-Key"])
        return httpx.Response(200, json=expected)

    with client(tmp_path, identity, handle) as delivery:
        interrupted = delivery.enqueue(pair)
        confirmed = delivery.enqueue(pair)
        confirmed_result = delivery.send(confirmed)
    with sqlite3.connect(tmp_path / "queue.sqlite3") as conn:
        conn.execute(
            "UPDATE deliveries SET status='SENDING',attempts=2 WHERE idempotency_key=?",
            (interrupted,),
        )
    with client(tmp_path, identity, handle) as restarted:
        assert restarted.get(interrupted)["status"] == "PENDING"
        assert restarted.get(interrupted)["attempts"] == 2
        assert restarted.get(confirmed) == confirmed_result
        results = restarted.resume_pending()
        assert len(results) == 1
        assert results[0]["status"] == "CONFIRMED"
        assert results[0]["attempts"] == 3
        assert results[0]["idempotency_key"] == interrupted
        assert sent_keys == [confirmed, interrupted]


def test_response_lost_retry_uses_same_key(tmp_path, identity, pair):
    received = []
    issued = certificate(pair, identity[0])
    sleeps = []

    def handle(request):
        received.append(request.headers["Idempotency-Key"])
        if len(received) == 1:
            raise httpx.ReadTimeout("synthetic committed reply lost", request=request)
        return httpx.Response(200, json=issued)

    with client(tmp_path, identity, handle, sleep=sleeps.append) as delivery:
        key = delivery.enqueue(pair)
        result = delivery.send(key)
        assert result["status"] == "CONFIRMED"
        assert result["attempts"] == 2
    assert received == [key, key]
    assert len(sleeps) == 1 and 1 <= sleeps[0] <= 1.25


@pytest.mark.parametrize("failure", ["network", 408, 429, 500, 503])
def test_five_attempt_bound_leaves_pending(tmp_path, identity, pair, failure):
    sent_keys, sleeps = [], []

    def handle(request):
        sent_keys.append(request.headers["Idempotency-Key"])
        if failure == "network":
            raise httpx.ConnectError("synthetic unavailable", request=request)
        return httpx.Response(failure)

    with client(tmp_path, identity, handle, sleep=sleeps.append) as delivery:
        key = delivery.enqueue(pair)
        result = delivery.send(key)
        assert result["status"] == "PENDING"
        assert "certificate" not in result
        assert result["attempts"] == 5
        assert result["error"]["code"] in {"NETWORK_ERROR", "RETRYABLE_HTTP"}
    assert sent_keys == [key] * 5
    assert len(sleeps) == 4
    assert all(expected <= actual <= expected + 0.25 for expected, actual in zip([1, 2, 4, 8], sleeps))


def test_explicit_resume_keeps_key_and_accumulates_attempt_count(tmp_path, identity, pair):
    calls = []
    available = False

    def handle(request):
        calls.append(request.headers["Idempotency-Key"])
        return httpx.Response(201, json=certificate(pair, identity[0])) if available else httpx.Response(503)

    with client(tmp_path, identity, handle, max_attempts=2) as delivery:
        key = delivery.enqueue(pair)
        assert delivery.send(key)["attempts"] == 2
        available = True
        result = delivery.resume_pending()[0]
        assert result["status"] == "CONFIRMED"
        assert result["attempts"] == 3
    assert calls == [key] * 3


def test_retry_after_is_respected_with_injected_sleep(tmp_path, identity, pair):
    calls, sleeps = [], []

    def handle(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(429, headers={"Retry-After": "7"})
        return httpx.Response(201, json=certificate(pair, identity[0]))

    with client(tmp_path, identity, handle, sleep=sleeps.append) as delivery:
        assert delivery.send(delivery.enqueue(pair))["status"] == "CONFIRMED"
    assert sleeps == [7.0]


@pytest.mark.parametrize("header", ["3600", "inf", "Sat, 10 Oct 2099 10:00:00 GMT"])
def test_long_retry_after_defers_without_early_retry(tmp_path, identity, pair, header):
    calls, sleeps = [], []

    def handle(request):
        calls.append(request)
        return httpx.Response(429, headers={"Retry-After": header})

    with client(tmp_path, identity, handle, sleep=sleeps.append) as delivery:
        result = delivery.send(delivery.enqueue(pair))
        assert result["status"] == "PENDING"
        assert result["error"]["deferred"] == "RETRY_AFTER_EXCEEDS_WAIT_BUDGET"
    assert len(calls) == 1
    assert sleeps == []


def test_retry_after_has_cumulative_execution_budget(tmp_path, identity, pair):
    calls, sleeps = [], []

    def handle(request):
        calls.append(request)
        return httpx.Response(503, headers={"Retry-After": "20"})

    with client(tmp_path, identity, handle, sleep=sleeps.append) as delivery:
        result = delivery.send(delivery.enqueue(pair))
        assert result["status"] == "PENDING"
        assert result["attempts"] == 2
        assert result["error"]["deferred"] == "RETRY_AFTER_EXCEEDS_WAIT_BUDGET"
    assert sleeps == [20.0]
    assert len(calls) == 2


def test_deferred_retry_after_survives_restart_without_early_send(tmp_path, identity, pair, monkeypatch):
    calls = []

    def handle(request):
        calls.append(request.headers["Idempotency-Key"])
        if len(calls) == 1:
            return httpx.Response(429, headers={"Retry-After": "3600"})
        return httpx.Response(200, json=certificate(pair, identity[0]))

    with client(tmp_path, identity, handle) as delivery:
        key = delivery.enqueue(pair)
        pending = delivery.send(key)
        assert pending["status"] == "PENDING"
        assert delivery.send(key) == pending
    with client(tmp_path, identity, handle) as restarted:
        assert restarted.resume_pending() == [pending]
        assert calls == [key]
        deadline = pending["error"]["retry_not_before"]
        monkeypatch.setattr("iahash_client.time.time", lambda: deadline + 1)
        result = restarted.resume_pending()[0]
        assert result["status"] == "CONFIRMED"
        assert result["attempts"] == 2
    assert calls == [key, key]


@pytest.mark.parametrize("attempts", [1, 5])
@pytest.mark.parametrize("header", ["7", "3600"])
def test_last_attempt_retry_after_is_durable(tmp_path, identity, pair, monkeypatch, attempts, header):
    calls = []

    def handle(request):
        calls.append(request.headers["Idempotency-Key"])
        if len(calls) <= attempts:
            headers = {"Retry-After": header} if len(calls) == attempts else {}
            return httpx.Response(429, headers=headers)
        return httpx.Response(200, json=certificate(pair, identity[0]))

    with client(tmp_path, identity, handle, max_attempts=attempts) as delivery:
        key = delivery.enqueue(pair)
        pending = delivery.send(key)
        assert pending["status"] == "PENDING"
        assert pending["attempts"] == attempts
        assert pending["error"]["retry_not_before"] > 0
        assert delivery.send(key) == pending
    with client(tmp_path, identity, handle, max_attempts=attempts) as restarted:
        assert restarted.resume_pending() == [pending]
        assert len(calls) == attempts
        deadline = pending["error"]["retry_not_before"]
        monkeypatch.setattr("iahash_client.time.time", lambda: deadline + 1)
        result = restarted.send(key)
        assert result["status"] == "CONFIRMED"
        assert result["attempts"] == attempts + 1
    assert calls == [key] * (attempts + 1)


def test_interrupted_retry_wait_keeps_deadline(tmp_path, identity, pair):
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(429, headers={"Retry-After": "7"})

    def interrupted_sleep(_):
        raise InterruptedError("synthetic interrupted wait")

    with client(tmp_path, identity, handle, sleep=interrupted_sleep) as delivery:
        key = delivery.enqueue(pair)
        with pytest.raises(InterruptedError):
            delivery.send(key)
        assert delivery.get(key)["status"] == "PENDING"
    with client(tmp_path, identity, handle) as restarted:
        assert restarted.send(key)["status"] == "PENDING"
    assert len(calls) == 1


class TrackingStream(httpx.SyncByteStream):
    def __init__(self, chunks):
        self.chunks = chunks
        self.reads = 0
        self.closed = False

    def __iter__(self):
        for chunk in self.chunks:
            self.reads += 1
            yield chunk

    def close(self):
        self.closed = True


def test_streaming_cap_stops_unknown_length_response_early(tmp_path, identity, pair):
    stream = TrackingStream(b"x" * 1024 for _ in range(10_000))
    with client(tmp_path, identity, lambda _: httpx.Response(201, stream=stream)) as delivery:
        result = delivery.send(delivery.enqueue(pair))
        assert result["status"] == "REJECTED"
        assert result["error"]["code"] == "CERTIFICATE_TOO_LARGE"
    assert stream.reads == 17
    assert stream.closed


def test_streaming_cap_rejects_declared_oversize_without_reading(tmp_path, identity, pair):
    stream = TrackingStream([b"unread synthetic oversize body"])
    with client(tmp_path, identity, lambda _: httpx.Response(
        201, headers={"Content-Length": "1000000"}, stream=stream,
    )) as delivery:
        result = delivery.send(delivery.enqueue(pair))
        assert result["error"]["code"] == "CERTIFICATE_TOO_LARGE"
    assert stream.reads == 0
    assert stream.closed


def test_compressed_response_rejected_before_decompression(tmp_path, identity, pair):
    stream = TrackingStream([b"unread potentially expansive compressed data"])

    def handle(request):
        assert request.headers["Accept-Encoding"] == "identity"
        return httpx.Response(201, headers={"Content-Encoding": "gzip"}, stream=stream)

    with client(tmp_path, identity, handle) as delivery:
        result = delivery.send(delivery.enqueue(pair))
        assert result["status"] == "REJECTED"
        assert result["error"]["code"] == "UNSUPPORTED_CONTENT_ENCODING"
    assert stream.reads == 0
    assert stream.closed


def test_streamed_valid_envelope_preserves_exact_bytes(tmp_path, identity, pair):
    expected = json.dumps(certificate(pair, identity[0]), indent=2).encode("ascii")
    stream = TrackingStream(expected[index:index + 17] for index in range(0, len(expected), 17))
    with client(tmp_path, identity, lambda _: httpx.Response(201, stream=stream)) as delivery:
        result = delivery.send(delivery.enqueue(pair))
        assert result["status"] == "CONFIRMED"
    with sqlite3.connect(tmp_path / "queue.sqlite3") as conn:
        assert conn.execute("SELECT certificate FROM deliveries").fetchone()[0] == expected
    assert stream.closed


def test_midstream_network_failure_stays_pending(tmp_path, identity, pair):
    class InterruptedStream(TrackingStream):
        def __iter__(self):
            yield b'{"body":'
            raise httpx.ReadError("synthetic interrupted response")

    stream = InterruptedStream([])
    with client(tmp_path, identity, lambda _: httpx.Response(201, stream=stream), max_attempts=1) as delivery:
        result = delivery.send(delivery.enqueue(pair))
        assert result["status"] == "PENDING"
        assert result["error"]["code"] == "NETWORK_ERROR"
        assert "certificate" not in result
    assert stream.closed


@pytest.mark.parametrize("status", [302, 400, 503])
def test_noncertificate_response_body_is_not_read(tmp_path, identity, pair, status):
    stream = TrackingStream(b"x" * 1024 for _ in range(10_000))
    with client(tmp_path, identity, lambda _: httpx.Response(status, stream=stream), max_attempts=1) as delivery:
        result = delivery.send(delivery.enqueue(pair))
        assert result["status"] == ("PENDING" if status == 503 else "REJECTED")
    assert stream.reads == 0
    assert stream.closed


@pytest.mark.parametrize("status", [400, 401, 403, 404, 409, 422, 302, 307])
def test_http_rejection_never_retries_or_follows_redirect(tmp_path, identity, pair, status):
    urls = []

    def handle(request):
        urls.append(str(request.url))
        return httpx.Response(status, headers={"Location": "https://other-origin.test/steal"})

    with client(tmp_path, identity, handle) as delivery:
        result = delivery.send(delivery.enqueue(pair))
        assert result["status"] == "REJECTED"
        assert result["error"] == {"code": "HTTP_REJECTED", "http_status": status}
        assert delivery.send(result["idempotency_key"]) == result
        assert delivery.resume_pending() == []
    assert urls == ["https://issuer.test/api/pair-v1/receipts"]


@pytest.mark.parametrize("case", ["wrong_pair", "wrong_environment", "unknown_issuer", "bad_signature", "bad_pair_id"])
def test_invalid_or_unrelated_certificate_is_rejected(tmp_path, identity, pair, case):
    cert = certificate(pair, identity[0])
    if case == "wrong_pair":
        cert = certificate(make_pair("Different", "Pair"), identity[0])
    elif case == "wrong_environment":
        cert = certificate(pair, identity[0], environment="PRODUCTION")
    elif case == "unknown_issuer":
        cert = certificate(pair, identity[0], issuer="untrusted-issuer")
    elif case == "bad_signature":
        cert["signature"] = "0" * 128
    else:
        cert["body"]["pair_id"] = "0" * 64
    with client(tmp_path, identity, lambda _: httpx.Response(201, json=cert)) as delivery:
        result = delivery.send(delivery.enqueue(pair))
        assert result["status"] == "REJECTED"
        assert "certificate" not in result
        assert result["error"]["code"] in {"INVALID_CERTIFICATE", "REQUEST_PAIR_MISMATCH"}
        assert result["attempts"] == 1


@pytest.mark.parametrize("data", [b"not json", b'{"body":{},"body":{}}', b"x" * (16 * 1024 + 1)])
def test_malformed_response_is_rejected_without_persisting_untrusted_content(tmp_path, identity, pair, data):
    with client(tmp_path, identity, lambda _: httpx.Response(201, content=data)) as delivery:
        result = delivery.send(delivery.enqueue(pair))
        assert result["status"] == "REJECTED"
        assert "certificate" not in result
        assert result["error"]["code"] in {"MALFORMED_CERTIFICATE", "CERTIFICATE_TOO_LARGE"}


@pytest.mark.parametrize("base_url,environment,allowed", [
    ("http://localhost:8000", "LAB", False),
    ("http://127.0.0.1:8000", "PRODUCTION", True),
    ("http://localhost:8000", "STAGING", True),
    ("http://issuer.test", "LAB", True),
    ("http://127.0.0.2", "LAB", True),
    ("https://user:password@issuer.test", "LAB", False),
    ("https://issuer.test?token=secret", "LAB", False),
    ("https://issuer.test#fragment", "LAB", False),
    ("https://issuer.test/legacy", "LAB", False),
    ("https://issuer.test\\@evil.test", "LAB", False),
    ("https://issuer.test:99999", "LAB", False),
])
def test_unsafe_endpoint_configuration_rejected_before_queue_creation(tmp_path, identity, base_url, environment, allowed):
    with pytest.raises(ValueError):
        client(
            tmp_path, identity, lambda _: pytest.fail("must not send"),
            base_url=base_url, expected_environment=environment,
            allow_insecure_localhost=allowed,
        )
    assert not (tmp_path / "queue.sqlite3").exists()


@pytest.mark.parametrize("host", ["localhost", "127.0.0.1", "[::1]"])
def test_explicit_lab_loopback_http_allowed(tmp_path, identity, host):
    with client(
        tmp_path, identity, lambda _: pytest.fail("must not send"),
        base_url=f"http://{host}:8000/api/pair-v1/", allow_insecure_localhost=True,
    ) as delivery:
        assert delivery.base_url == f"http://{host}:8000/api/pair-v1/receipts"


@pytest.mark.parametrize("contents", [b"", b"corrupt queue: preserve evidence"])
def test_empty_or_corrupt_queue_is_preserved(tmp_path, identity, contents):
    path = tmp_path / "queue.sqlite3"
    path.write_bytes(contents)
    with pytest.raises(QueueError):
        client(tmp_path, identity, lambda _: pytest.fail("must not send"))
    assert path.read_bytes() == contents


def test_unknown_queue_schema_is_preserved(tmp_path, identity):
    path = tmp_path / "queue.sqlite3"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE historical_evidence(value TEXT)")
        conn.execute("INSERT INTO historical_evidence VALUES ('retain-me')")
    original = path.read_bytes()
    with pytest.raises(QueueError, match="Unknown queue schema"):
        client(tmp_path, identity, lambda _: pytest.fail("must not send"))
    assert path.read_bytes() == original


@pytest.mark.parametrize("changed", ["environment", "endpoint", "issuers"])
def test_existing_queue_cannot_switch_identity_binding(tmp_path, identity, pair, changed):
    with client(tmp_path, identity, lambda _: pytest.fail("must not send")) as delivery:
        key = delivery.enqueue(pair)
    options = {}
    if changed == "environment":
        options["expected_environment"] = "STAGING"
    elif changed == "endpoint":
        options["base_url"] = "https://different.test"
    else:
        options["trusted_keys"] = {}
    with pytest.raises(QueueError, match="binding differs"):
        client(tmp_path, identity, lambda _: pytest.fail("must not send"), **options)
    with client(tmp_path, identity, lambda _: pytest.fail("must not send")) as delivery:
        assert delivery.get(key)["status"] == "PENDING"


def test_invalid_pair_is_not_enqueued_and_closed_client_refuses_use(tmp_path, identity, pair):
    with client(tmp_path, identity, lambda _: pytest.fail("must not send")) as delivery:
        invalid = {**pair, "original": "do not persist"}
        with pytest.raises(ValueError):
            delivery.enqueue(invalid)
        assert delivery.resume_pending() == []
    with pytest.raises(RuntimeError, match="closed"):
        delivery.enqueue(pair)


@pytest.mark.parametrize("attempts", [0, 6, True, 1.5])
def test_attempt_limit_cannot_exceed_contract(tmp_path, identity, attempts):
    with pytest.raises(ValueError, match="max_attempts"):
        client(tmp_path, identity, lambda _: pytest.fail("must not send"), max_attempts=attempts)
