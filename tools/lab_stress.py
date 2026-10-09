"""Bounded synthetic concurrency trial, in-process; never targets an external URL.

This measures request concurrency (1/3/6), not the number of Codex agents.
No conclusion about WinWork or Cloud capacity follows from this host's result.
"""
from __future__ import annotations

import argparse
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import secrets
import sqlite3
import tempfile
import time

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from iahash_core import key_id, make_pair, verify_receipt
from iahash_server.app import create_app


def run_trial(concurrency: int, pairs: int = 12) -> dict:
    if concurrency not in (1, 3, 6) or not 1 <= pairs <= 12:
        raise ValueError("Trial permits only 1/3/6 threads and up to 12 synthetic pairs")
    with tempfile.TemporaryDirectory(prefix="iahash-lab-") as directory:
        db = Path(directory) / "registry.sqlite"
        sk = Ed25519PrivateKey.generate()
        token = secrets.token_hex(32)
        app = create_app(db_path=db, private_key=sk, issuer_id="stress.lab",
                         environment="LAB", api_token=token)
        trust = {("stress.lab", "LAB", key_id(sk.public_key())): sk.public_key()}
        entries = [(make_pair(f"Synthetic {i}", f"Result {i}"), secrets.token_hex(32))
                   for i in range(pairs)]
        latencies = []
        started = time.monotonic()
        with TestClient(app) as server:
            def submit(entry):
                pair, idem = entry
                before = time.monotonic()
                response = server.post("/api/pair-v1/receipts", json=pair, headers={
                    "Authorization": f"Bearer {token}", "Idempotency-Key": idem})
                duration = time.monotonic() - before
                if response.status_code not in (200, 201, 429, 503):
                    raise AssertionError((response.status_code, response.text))
                if response.status_code in (200, 201):
                    certificate = response.json()
                    assert verify_receipt(certificate, trusted_keys=trust,
                                          expected_environment="LAB")["status"] == "VERIFIED_RECEIPT"
                    return idem, response.status_code, certificate, duration
                return idem, response.status_code, None, duration
            with ThreadPoolExecutor(max_workers=concurrency) as pool:
                results = list(pool.map(submit, entries + entries))
            confirmed = {}
            for idem, status, certificate, duration in results:
                latencies.append(duration)
                if certificate is not None:
                    assert confirmed.setdefault(idem, certificate) == certificate
            initial_confirmed = len(confirmed)
            # Drain the bounded backlog after the wave and compare two successful
            # responses per key. A wholly unavailable service must never pass.
            if any(row[1] == 429 for row in results):
                time.sleep(1)  # The synthetic write-limit Retry-After is one second.
            for entry in entries:
                for _ in range(2):
                    idem, status, certificate, _ = submit(entry)
                    assert status in (200, 201), 'Bounded recovery did not complete'
                    assert confirmed.setdefault(idem, certificate) == certificate
            with closing(sqlite3.connect(db)) as conn:
                count = conn.execute("SELECT COUNT(*) FROM receipts").fetchone()[0]
                assert conn.execute("PRAGMA integrity_check").fetchone() == ("ok",)
            assert count == len(confirmed) == pairs
        elapsed = time.monotonic() - started
        latencies.sort()
        return {"concurrency": concurrency, "pairs_requested": pairs,
                "wave_requests": len(results), "recovery_requests": pairs * 2,
                "initial_confirmed_receipts": initial_confirmed, "confirmed_receipts": count,
                "statuses": {str(code): sum(row[1] == code for row in results)
                             for code in sorted({row[1] for row in results})},
                "elapsed_seconds": round(elapsed, 4),
                "p95_seconds": round(latencies[min(len(latencies)-1, int(len(latencies)*.95))], 4),
                "integrity": "PASS", "idempotency": "PASS", "signatures": "PASS"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    # There is deliberately no URL, unbounded iteration or arbitrary worker option.
    results = {"environment": "LAB", "host_label": "caller-supplied-in-private-log",
               "logical_cpus_observed": os.cpu_count(),
               "scope": "synthetic request concurrency, not agent capacity or production throughput",
               "trials": [run_trial(n) for n in (1, 3, 6)]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(results, stream, indent=2)
        stream.write("\n")
    print("PASS: bounded LAB trials; evidence written to", args.output)


if __name__ == "__main__":
    main()
