"""Durable hash-only delivery client for the isolated IA-HASH PAIR-1 API."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
import math
from pathlib import Path
import re
import secrets
import sqlite3
import threading
import time
from urllib.parse import urlsplit

import httpx

from iahash_core import (
    canonical_bytes, derive_pair_id, strict_json_loads, validate_pair, verify_receipt,
)


class QueueError(RuntimeError):
    """The local queue is incompatible or cannot safely be used."""


class Client:
    """Persist requests before transport; confirm only trusted matching receipts.

    This queue is intended for one active client process. On process restart,
    interrupted SENDING deliveries become PENDING with the same idempotency key.
    No original content, API tokens or private keys are stored in the queue.
    """

    MAX_RETRY_WAIT = 30.0
    MAX_CERTIFICATE_BYTES = 16 * 1024

    def __init__(
        self, *, base_url: str, queue_path: Path, api_token: str,
        trusted_keys: dict, expected_environment: str,
        transport: httpx.BaseTransport | None = None, max_attempts: int = 5,
        sleep=time.sleep, allow_insecure_localhost: bool = False,
    ):
        if expected_environment not in {"LAB", "STAGING", "PRODUCTION"}:
            raise ValueError("An explicit supported environment is required")
        if type(max_attempts) is not int or not 1 <= max_attempts <= 5:
            raise ValueError("max_attempts must be between 1 and 5")
        if not isinstance(api_token, str) or not api_token or any(
            char in api_token for char in "\r\n"
        ):
            raise ValueError("A nonempty API token without line breaks is required")
        if not isinstance(trusted_keys, dict) or any(
            not isinstance(key, tuple) or len(key) != 3
            or not all(isinstance(part, str) for part in key)
            for key in trusted_keys
        ):
            raise ValueError("Trust keys must use (issuer_id, environment, key_id)")
        self.expected_environment = expected_environment
        self.trusted_keys = dict(trusted_keys)
        self.max_attempts = max_attempts
        self.sleep = sleep
        self.queue_path = Path(queue_path)
        self._lock = threading.RLock()
        self._closed = False
        self.base_url = self._endpoint(
            base_url, expected_environment, allow_insecure_localhost
        )
        self._metadata = {
            "endpoint": self.base_url,
            "environment": expected_environment,
            "issuers": json.dumps(sorted({
                issuer for issuer, environment, _ in trusted_keys
                if environment == expected_environment
            }), separators=(",", ":")),
        }
        self._initialize_queue()
        self._http = httpx.Client(
            transport=transport, follow_redirects=False, trust_env=False,
            timeout=httpx.Timeout(10.0, connect=3.0),
            headers={"Authorization": "Bearer " + api_token},
        )

    @staticmethod
    def _endpoint(base_url, environment, allow_insecure):
        if not isinstance(base_url, str) or any(c.isspace() for c in base_url):
            raise ValueError("A valid explicit API base URL is required")
        try:
            parsed = urlsplit(base_url)
            port = parsed.port
        except ValueError as exc:
            raise ValueError("Invalid API base URL") from exc
        if (
            not parsed.hostname or parsed.username is not None
            or parsed.password is not None or parsed.query or parsed.fragment
            or parsed.path.rstrip("/") not in {"", "/api/pair-v1"}
            or "\\" in base_url or (port is not None and port < 1)
        ):
            raise ValueError("Base URL must be an origin or the PAIR-1 API prefix")
        local = parsed.hostname.lower() in {"localhost", "127.0.0.1", "::1"}
        if parsed.scheme != "https" and not (
            parsed.scheme == "http" and local and environment == "LAB"
            and allow_insecure is True
        ):
            raise ValueError("HTTPS required; explicit loopback HTTP is LAB-only")
        host = parsed.hostname.lower()
        if ":" in host:
            host = "[" + host + "]"
        default_port = 443 if parsed.scheme == "https" else 80
        authority = host + (":" + str(port) if port and port != default_port else "")
        return parsed.scheme + "://" + authority + "/api/pair-v1/receipts"

    @contextmanager
    def _connection(self):
        conn = sqlite3.connect(self.queue_path, timeout=5, isolation_level=None)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute("PRAGMA synchronous=FULL")
            yield conn
        finally:
            conn.close()

    def _initialize_queue(self):
        self.queue_path.parent.mkdir(parents=True, exist_ok=True)
        existed = self.queue_path.exists()
        if existed and self.queue_path.stat().st_size == 0:
            raise QueueError("Existing empty queue preserved; initialization refused")
        try:
            with self._connection() as conn:
                conn.execute("BEGIN IMMEDIATE")
                version = conn.execute("PRAGMA user_version").fetchone()[0]
                tables = {row[0] for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )}
                if not tables and version == 0 and not existed:
                    conn.execute("CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
                    conn.execute("""CREATE TABLE deliveries (
                        idempotency_key TEXT PRIMARY KEY,
                        pair BLOB NOT NULL,
                        status TEXT NOT NULL CHECK(status IN ('PENDING','SENDING','CONFIRMED','REJECTED')),
                        attempts INTEGER NOT NULL DEFAULT 0,
                        certificate BLOB,
                        error TEXT
                    )""")
                    conn.executemany("INSERT INTO metadata VALUES (?, ?)", self._metadata.items())
                    conn.execute("PRAGMA user_version=1")
                else:
                    if version != 1 or tables != {"metadata", "deliveries"}:
                        raise QueueError("Unknown queue schema preserved; migration refused")
                    expected_columns = {
                        "idempotency_key", "pair", "status", "attempts", "certificate", "error"
                    }
                    if {row[1] for row in conn.execute("PRAGMA table_info(deliveries)")} != expected_columns:
                        raise QueueError("Unknown queue columns preserved")
                    metadata = dict(conn.execute("SELECT key, value FROM metadata"))
                    if metadata != self._metadata:
                        raise QueueError("Queue endpoint, environment or issuer binding differs")
                conn.execute("UPDATE deliveries SET status='PENDING' WHERE status='SENDING'")
                conn.commit()
                conn.execute("PRAGMA journal_mode=WAL")
        except QueueError:
            raise
        except sqlite3.Error as exc:
            raise QueueError("Queue initialization failed; evidence preserved") from exc

    def _check_open(self):
        if self._closed:
            raise RuntimeError("Client is closed")

    @staticmethod
    def _check_key(key):
        if not isinstance(key, str) or re.fullmatch(r"[0-9a-f]{64}", key) is None:
            raise ValueError("Invalid idempotency key")

    @staticmethod
    def _result(row):
        result = {
            "idempotency_key": row["idempotency_key"],
            "status": row["status"], "attempts": row["attempts"],
        }
        if row["certificate"] is not None:
            result["certificate"] = strict_json_loads(row["certificate"])
        if row["error"] is not None:
            result["error"] = json.loads(row["error"])
        return result

    def get(self, key: str) -> dict:
        """Read durable delivery status without initiating transport."""
        self._check_open()
        self._check_key(key)
        with self._connection() as conn:
            row = conn.execute("SELECT * FROM deliveries WHERE idempotency_key=?", (key,)).fetchone()
        if row is None:
            raise KeyError(key)
        return self._result(row)

    def enqueue(self, pair: dict) -> str:
        self._check_open()
        encoded = canonical_bytes(validate_pair(pair))
        key = secrets.token_hex(32)
        with self._lock, self._connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                "INSERT INTO deliveries(idempotency_key,pair,status) VALUES (?,?,'PENDING')",
                (key, encoded),
            )
            conn.commit()
        return key

    def _claim(self, key):
        with self._connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute("SELECT * FROM deliveries WHERE idempotency_key=?", (key,)).fetchone()
            if row is None:
                raise KeyError(key)
            if row["status"] != "PENDING":
                conn.commit()
                return None, self._result(row)
            error = json.loads(row["error"]) if row["error"] else {}
            not_before = error.get("retry_not_before", 0)
            if not_before == "indefinite" or not_before > time.time():
                conn.commit()
                return None, self._result(row)
            pair = validate_pair(strict_json_loads(row["pair"]))
            conn.execute(
                "UPDATE deliveries SET status='SENDING',attempts=attempts+1 WHERE idempotency_key=?",
                (key,),
            )
            conn.commit()
        return pair, None

    def _finish(self, key, status, *, certificate=None, error=None):
        with self._connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            # A confirmed historical receipt is immutable, even if another
            # sender completes after it. Never replace or clear its envelope.
            conn.execute(
                "UPDATE deliveries SET status=?,certificate=?,error=? "
                "WHERE idempotency_key=? AND status!='CONFIRMED'",
                (status, certificate, json.dumps(error) if error else None, key),
            )
            conn.commit()
        return self.get(key)

    @staticmethod
    def _retry_after(value):
        if value is None:
            return 0.0
        try:
            seconds = float(value)
            if not math.isfinite(seconds):
                return math.inf if seconds > 0 else 0.0
            return max(0.0, seconds)
        except (TypeError, ValueError):
            try:
                parsed = parsedate_to_datetime(value)
                if parsed.tzinfo is None:
                    return 0.0
                return max(0.0, (parsed - datetime.now(timezone.utc)).total_seconds())
            except (TypeError, ValueError, OverflowError):
                return 0.0

    def send(self, key: str) -> dict:
        self._check_open()
        self._check_key(key)
        with self._lock:
            waited = 0.0
            for attempt in range(self.max_attempts):
                pair, existing = self._claim(key)
                if existing is not None:
                    return existing
                retry_after = 0.0
                try:
                    with self._http.stream(
                        "POST", self.base_url, content=canonical_bytes(pair),
                        headers={"Content-Type": "application/json", "Idempotency-Key": key,
                                 "Accept-Encoding": "identity"},
                    ) as response:
                        status = response.status_code
                        if status in {200, 201}:
                            return self._read_confirmation(key, pair, response)
                        if status not in {408, 429} and not 500 <= status <= 599:
                            return self._finish(key, "REJECTED", error={
                                "code": "HTTP_REJECTED", "http_status": status,
                            })
                        error = {"code": "RETRYABLE_HTTP", "http_status": status}
                        retry_after = self._retry_after(response.headers.get("Retry-After"))
                except httpx.RequestError as exc:
                    error = {"code": "NETWORK_ERROR", "type": type(exc).__name__}
                if retry_after > 0:
                    # Persist before any return or wait, including the last
                    # allowed attempt. A restart cannot bypass Retry-After.
                    error["retry_not_before"] = (
                        time.time() + retry_after
                        if math.isfinite(retry_after) else "indefinite"
                    )
                result = self._finish(key, "PENDING", error=error)
                if result["status"] != "PENDING" or attempt + 1 == self.max_attempts:
                    return result
                jitter = secrets.randbelow(251) / 1000.0
                delay = max(float(2 ** attempt) + jitter, retry_after)
                if delay > self.MAX_RETRY_WAIT - waited:
                    return self._finish(key, "PENDING", error={
                        **error, "deferred": "RETRY_AFTER_EXCEEDS_WAIT_BUDGET",
                    })
                self.sleep(delay)
                waited += delay
                if "retry_not_before" in error:
                    # The injected sleep represents completion of the wait.
                    # If it raises or the process dies, the deadline remains.
                    error.pop("retry_not_before")
                    result = self._finish(key, "PENDING", error=error)
                    if result["status"] != "PENDING":
                        return result
        raise AssertionError("Unreachable delivery state")

    def _read_confirmation(self, key, pair, response):
        # Request identity encoding and reject compressed responses before
        # decoding: the byte bound must also resist decompression expansion.
        if response.headers.get("Content-Encoding", "").strip().lower() not in {"", "identity"}:
            return self._finish(key, "REJECTED", error={"code": "UNSUPPORTED_CONTENT_ENCODING"})
        try:
            declared = int(response.headers.get("Content-Length", "0"))
        except ValueError:
            declared = 0
        if declared > self.MAX_CERTIFICATE_BYTES:
            return self._finish(key, "REJECTED", error={"code": "CERTIFICATE_TOO_LARGE"})
        if response.is_stream_consumed:
            # MockTransport may receive a caller-prebuffered Response. The
            # real HTTP transport remains unconsumed when using stream().
            return self._confirm(key, pair, response.content)
        data = bytearray()
        for chunk in response.iter_raw(chunk_size=1024):
            if len(data) + len(chunk) > self.MAX_CERTIFICATE_BYTES:
                return self._finish(key, "REJECTED", error={"code": "CERTIFICATE_TOO_LARGE"})
            data.extend(chunk)
        return self._confirm(key, pair, bytes(data))

    def _confirm(self, key, pair, data):
        if len(data) > self.MAX_CERTIFICATE_BYTES:
            return self._finish(key, "REJECTED", error={"code": "CERTIFICATE_TOO_LARGE"})
        try:
            certificate = strict_json_loads(data)
            verification = verify_receipt(
                certificate, trusted_keys=self.trusted_keys,
                expected_environment=self.expected_environment,
            )
            if verification["status"] != "VERIFIED_RECEIPT":
                return self._finish(key, "REJECTED", error={
                    "code": "INVALID_CERTIFICATE", "verification": verification,
                })
            body = certificate["body"]
            if body["pair_id"] != derive_pair_id(pair) or body["pair"] != pair:
                return self._finish(key, "REJECTED", error={"code": "REQUEST_PAIR_MISMATCH"})
        except (ValueError, KeyError, TypeError) as exc:
            return self._finish(key, "REJECTED", error={
                "code": "MALFORMED_CERTIFICATE", "type": type(exc).__name__,
            })
        return self._finish(key, "CONFIRMED", certificate=data)

    def resume_pending(self) -> list[dict]:
        self._check_open()
        with self._connection() as conn:
            keys = [row[0] for row in conn.execute(
                "SELECT idempotency_key FROM deliveries WHERE status='PENDING' ORDER BY rowid"
            )]
        return [self.send(key) for key in keys]

    def close(self):
        if not self._closed:
            self._http.close()
            self._closed = True

    def __enter__(self):
        self._check_open()
        return self

    def __exit__(self, *_):
        self.close()


__all__ = ["Client", "QueueError"]
