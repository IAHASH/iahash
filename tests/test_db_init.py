from __future__ import annotations

import logging
import sqlite3
import subprocess

import pytest

from iahash import db


def test_ensure_db_initialized_without_sqlite_binary(tmp_path, monkeypatch, caplog):
    db_path = tmp_path / "iahash.db"
    schema = tmp_path / "schema.sql"
    seed = tmp_path / "seed.sql"

    schema.write_text("CREATE TABLE demo(id INTEGER);", encoding="utf-8")
    seed.write_text("INSERT INTO demo(id) VALUES (42);", encoding="utf-8")

    monkeypatch.setattr(db, "DB_PATH", db_path)
    monkeypatch.setattr(db, "SCHEMA_PATH", schema)
    monkeypatch.setattr(db, "SEED_PATH", seed)

    def fail_run(*args, **kwargs):
        raise AssertionError("External sqlite3 binary should not be invoked")

    monkeypatch.setattr(subprocess, "run", fail_run)
    caplog.set_level(logging.INFO)

    db.ensure_db_initialized()

    assert db_path.exists()
    with sqlite3.connect(db_path) as conn:
        value = conn.execute("SELECT id FROM demo").fetchone()[0]
    assert value == 42


def test_ensure_db_initialized_logs_on_error(tmp_path, monkeypatch, caplog):
    db_path = tmp_path / "iahash.db"
    schema = tmp_path / "schema.sql"

    schema.write_text("CREATE TABLE broken (id INTEGER PRIMARY KEY); INVALID", encoding="utf-8")

    monkeypatch.setattr(db, "DB_PATH", db_path)
    monkeypatch.setattr(db, "SCHEMA_PATH", schema)
    monkeypatch.setattr(db, "SEED_PATH", tmp_path / "missing_seed.sql")

    caplog.set_level(logging.ERROR)
    with pytest.raises(RuntimeError):
        db.ensure_db_initialized()

    assert any("Failed to initialize database" in message for message in caplog.messages)
    assert not db_path.exists()
