"""Optional, local reference receipt service. No legacy imports or network access."""
from __future__ import annotations

from collections import deque
import base64
import binascii
from datetime import datetime, timezone
import hashlib
import hmac
from pathlib import Path
import re
import sqlite3
import threading
import time
import uuid

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException

from iahash_core import (
    CoreValidationError, canonical_bytes, key_id, sign_receipt,
    strict_json_loads, validate_pair, verify_receipt,
)

PREFIX = "/api/pair-v1"
KEY_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
SCHEMA_VERSION = 1


def _error(code: str, message: str, status: int, retry_after: str | None = None):
    headers = {"Retry-After": retry_after} if retry_after else None
    return JSONResponse({"error": {"code": code, "message": message}},
                        status_code=status, headers=headers)


class _RequestPolicy:
    """Authenticate and bound raw ASGI bodies before JSON parsing."""

    def __init__(self, app, *, token: str, events: deque, lock: threading.Lock):
        self.app, self.token, self.events, self.lock = app, token, events, lock

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        path = scope.get("path", "")
        protected = path.startswith(PREFIX) and path not in {
            PREFIX + "/health", PREFIX + "/ready"}
        headers = {k.lower(): v for k, v in scope.get("headers", [])}
        if protected:
            expected = ("Bearer " + self.token).encode("utf-8")
            if not hmac.compare_digest(headers.get(b"authorization", b""), expected):
                return await _error("UNAUTHORIZED", "Bearer token required", 401)(scope, receive, send)
            now = time.monotonic()
            with self.lock:
                while self.events and self.events[0] <= now - 60:
                    self.events.popleft()
                limited = len(self.events) >= 60
                retry = max(1, int(61 - (now - self.events[0]))) if limited else 0
                if not limited:
                    self.events.append(now)
            if limited:
                return await _error("RATE_LIMITED", "Request limit reached", 429, str(retry))(scope, receive, send)
        if scope.get("method") != "POST":
            return await self.app(scope, receive, send)
        if headers.get(b"content-type", b"").split(b";", 1)[0].strip().lower() != b"application/json":
            return await _error("CONTENT_TYPE", "application/json required", 422)(scope, receive, send)
        maximum = 3 * 1024 * 1024 if path == PREFIX + "/verify" else 16 * 1024
        length = headers.get(b"content-length")
        if length is not None:
            try:
                declared = int(length)
                if declared < 0:
                    raise ValueError
            except ValueError:
                return await _error("INVALID_REQUEST", "Invalid content length", 400)(scope, receive, send)
            if declared > maximum:
                return await _error("BODY_TOO_LARGE", "Request body exceeds limit", 413)(scope, receive, send)
        chunks, count = [], 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            count += len(chunk)
            if count > maximum:
                return await _error("BODY_TOO_LARGE", "Request body exceeds limit", 413)(scope, receive, send)
            chunks.append(chunk)
            if not message.get("more_body", False):
                break
        scope["iahash.body"] = b"".join(chunks)
        delivered = False

        async def replay():
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": scope["iahash.body"], "more_body": False}
            return await receive()

        return await self.app(scope, replay, send)


def create_app(*, db_path: Path, private_key: Ed25519PrivateKey,
               issuer_id: str, environment: str, api_token: str,
               trusted_keys: dict | None = None) -> FastAPI:
    """Create an isolated service; caller explicitly supplies identity and key."""
    if not isinstance(private_key, Ed25519PrivateKey):
        raise ValueError("Ed25519 private key required")
    if not isinstance(issuer_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}", issuer_id):
        raise ValueError("Explicit valid issuer_id required")
    if environment not in {"LAB", "STAGING", "PRODUCTION"}:
        raise ValueError("Explicit environment required")
    if not isinstance(api_token, str) or not api_token:
        raise ValueError("Nonempty API token required")
    db_path = Path(db_path)
    public_key = private_key.public_key()
    identity = {"issuer_id": issuer_id, "environment": environment,
                "key_id": key_id(public_key)}
    trust = dict(trusted_keys or {})
    trust[(issuer_id, environment, identity["key_id"])] = public_key

    def connect(*, allow_create=False):
        target = str(db_path) if allow_create else db_path.resolve().as_uri() + "?mode=rw"
        connection = sqlite3.connect(target, uri=not allow_create, timeout=5, isolation_level=None)
        connection.execute("PRAGMA busy_timeout=5000")
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA synchronous=FULL")
        return connection

    def check_database(connection):
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        tables = {row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        if version != SCHEMA_VERSION or tables != {"identity", "receipts"}:
            raise RuntimeError("Unsupported receipt database schema")
        expected_columns = {
            "identity": ["name", "value"],
            "receipts": ["receipt_id", "idempotency_key", "request_digest", "certificate"],
        }
        for table, columns in expected_columns.items():
            if [r[1] for r in connection.execute(f"PRAGMA table_info({table})")] != columns:
                raise RuntimeError("Unsupported receipt database columns")
        recorded = dict(connection.execute("SELECT name, value FROM identity"))
        if recorded != identity:
            raise RuntimeError("Receipt database identity does not match configured issuer/key/environment")

    existed = db_path.exists()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = connect(allow_create=not existed)
    try:
        connection.execute("BEGIN IMMEDIATE")
        tables = connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        if not existed and not tables and version == 0:
            connection.execute("CREATE TABLE identity (name TEXT PRIMARY KEY, value TEXT NOT NULL)")
            connection.execute("CREATE TABLE receipts (receipt_id TEXT PRIMARY KEY, "
                               "idempotency_key TEXT NOT NULL UNIQUE, request_digest TEXT NOT NULL, "
                               "certificate BLOB NOT NULL)")
            connection.executemany("INSERT INTO identity VALUES (?, ?)", identity.items())
            connection.execute("PRAGMA user_version=1")
        check_database(connection)
        connection.commit()
        connection.execute("PRAGMA journal_mode=WAL")
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    app = FastAPI(title="IA-HASH reference receipt service", docs_url=None, redoc_url=None,
                  openapi_url=None)
    app.state.rate_events = deque()
    app.state.write_slots = threading.BoundedSemaphore(4)
    app.add_middleware(_RequestPolicy, token=api_token,
                       events=app.state.rate_events, lock=threading.Lock())

    def body(request):
        try:
            return strict_json_loads(request.scope.get("iahash.body", b""))
        except (CoreValidationError, ValueError, UnicodeError):
            return _error("INVALID_JSON", "Malformed or duplicate-key JSON", 400)

    @app.exception_handler(CoreValidationError)
    async def core_error(request, exc):
        return _error(getattr(exc, "code", "INVALID_SCHEMA"), "Input does not match the protocol schema", 422)

    @app.exception_handler(sqlite3.Error)
    async def database_error(request, exc):
        return _error("UNAVAILABLE", "Receipt storage unavailable", 503)

    @app.exception_handler(RuntimeError)
    async def service_error(request, exc):
        return _error("UNAVAILABLE", "Receipt service unavailable", 503)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request, exc):
        return _error("NOT_FOUND" if exc.status_code == 404 else "INVALID_REQUEST",
                      "Route not found" if exc.status_code == 404 else "Request is not supported",
                      exc.status_code)

    @app.exception_handler(Exception)
    async def unexpected_error(request, exc):
        return _error("INTERNAL_ERROR", "Receipt service error", 500)

    @app.get(PREFIX + "/health")
    def health():
        return {"status": "ok"}

    @app.get(PREFIX + "/ready")
    def ready():
        try:
            connection = connect()
            try:
                check_database(connection)
                connection.execute("SELECT receipt_id FROM receipts LIMIT 1").fetchall()
            finally:
                connection.close()
        except Exception:
            return _error("NOT_READY", "Service is not ready", 503)
        return {"status": "ready"}

    @app.get(PREFIX + "/issuer")
    def issuer():
        return {**identity, "pem": public_key.public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode("ascii")}

    @app.post(PREFIX + "/receipts")
    def issue(request: Request):
        pair = body(request)
        if isinstance(pair, Response):
            return pair
        pair = validate_pair(pair)
        idem = request.headers.get("Idempotency-Key", "")
        if not KEY_PATTERN.fullmatch(idem):
            return _error("INVALID_IDEMPOTENCY_KEY", "64 lowercase hex characters required", 422)
        if not app.state.write_slots.acquire(blocking=False):
            return _error("WRITE_LIMITED", "Concurrent write limit reached", 429, "1")
        connection = None
        try:
            digest = hashlib.sha256(canonical_bytes(pair)).hexdigest()
            connection = connect()
            connection.execute("BEGIN IMMEDIATE")
            check_database(connection)
            row = connection.execute(
                "SELECT request_digest, certificate FROM receipts WHERE idempotency_key=?", (idem,)).fetchone()
            if row:
                if row[0] != digest:
                    connection.rollback()
                    return _error("IDEMPOTENCY_CONFLICT", "Key already used for another pair", 409)
                certificate = bytes(row[1])
                connection.commit()
                return Response(certificate, status_code=200, media_type="application/json")
            for _ in range(5):
                receipt_id = str(uuid.uuid4())
                if not connection.execute("SELECT 1 FROM receipts WHERE receipt_id=?", (receipt_id,)).fetchone():
                    break
            else:
                connection.rollback()
                return _error("UNAVAILABLE", "Cannot allocate receipt identifier", 503)
            received_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            certificate = canonical_bytes(sign_receipt(
                pair, private_key, issuer_id=issuer_id, environment=environment,
                receipt_id=receipt_id, received_at=received_at))
            connection.execute("INSERT INTO receipts VALUES (?, ?, ?, ?)",
                               (receipt_id, idem, digest, certificate))
            connection.commit()
            return Response(certificate, status_code=201, media_type="application/json")
        except Exception:
            if connection is not None:
                connection.rollback()
            raise
        finally:
            if connection is not None:
                connection.close()
            app.state.write_slots.release()

    @app.get(PREFIX + "/receipts/{receipt_id}")
    def get_receipt(receipt_id: str):
        try:
            parsed = uuid.UUID(receipt_id)
            if parsed.version != 4 or str(parsed) != receipt_id:
                raise ValueError
        except ValueError:
            return _error("INVALID_RECEIPT_ID", "Canonical UUIDv4 required", 422)
        connection = connect()
        try:
            check_database(connection)
            row = connection.execute("SELECT certificate FROM receipts WHERE receipt_id=?", (receipt_id,)).fetchone()
        finally:
            connection.close()
        if row is None:
            return _error("NOT_FOUND", "Receipt not found", 404)
        return Response(bytes(row[0]), media_type="application/json")

    @app.post(PREFIX + "/verify")
    def verify(request: Request):
        payload = body(request)
        if isinstance(payload, Response):
            return payload
        if not isinstance(payload, dict) or "certificate" not in payload or set(payload) - {"certificate", "originals"}:
            return _error("INVALID_SCHEMA", "certificate and optional originals required", 422)
        if "originals" in payload and not isinstance(payload["originals"], dict):
            return _error("INVALID_ORIGINALS", "originals must be an object", 422)
        for supplied in (payload.get("originals") or {}).values():
            if not isinstance(supplied, dict):
                continue  # Core supplies the precise schema error.
            for field, value in supplied.items():
                if not isinstance(value, str):
                    continue
                try:
                    size = len(value.encode("utf-8")) if field == "text" else (
                        len(base64.b64decode(value, validate=True)) if field == "base64" else 0)
                except (ValueError, UnicodeError, binascii.Error):
                    continue  # Core rejects malformed encoding, never confirms it.
                if size > 1024 * 1024:
                    return _error("ORIGINAL_TOO_LARGE", "Each original is limited to 1 MiB", 413)
        result = verify_receipt(payload["certificate"], trusted_keys=trust,
                                expected_environment=environment, originals=payload.get("originals"))
        if result.get("schema") == "FAIL":
            return _error(result["status"], "Certificate schema is invalid or unsupported", 422)
        return result

    return app
