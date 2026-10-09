import sqlite3
import pytest
from iahash import db

def test_existing_registry_survives_unexpected_schema(tmp_path, monkeypatch):
    path = tmp_path / "registry.db"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE historical_evidence (value TEXT)")
        conn.execute("INSERT INTO historical_evidence VALUES ('retain-me')")
    schema = tmp_path / "schema.sql"
    schema.write_text("CREATE TABLE ignored (x TEXT)")
    monkeypatch.setattr(db, "DB_PATH", path)
    monkeypatch.setattr(db, "SCHEMA_PATH", schema)
    with pytest.raises(RuntimeError, match="preserved"):
        db.ensure_db_initialized()
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT value FROM historical_evidence").fetchone()[0] == "retain-me"

def test_existing_registry_survives_missing_schema(tmp_path, monkeypatch):
    path = tmp_path / "registry.db"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE historical_evidence (value TEXT)")
    monkeypatch.setattr(db, "DB_PATH", path)
    monkeypatch.setattr(db, "SCHEMA_PATH", tmp_path / "missing.sql")
    with pytest.raises(FileNotFoundError):
        db.ensure_db_initialized()
    assert path.exists()
