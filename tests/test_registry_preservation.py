import shutil
import sqlite3
import pytest
from iahash import db

def test_existing_registry_survives_unexpected_schema(tmp_path, monkeypatch):
    path = tmp_path / "registry.db"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE historical_evidence (value TEXT)")
        conn.execute("INSERT INTO historical_evidence VALUES ('retain-me')")
    original = path.read_bytes()
    schema = tmp_path / "schema.sql"
    schema.write_text("CREATE TABLE ignored (x TEXT)")
    monkeypatch.setattr(db, "DB_PATH", path)
    monkeypatch.setattr(db, "SCHEMA_PATH", schema)
    with pytest.raises(RuntimeError, match="preserved"):
        db.ensure_db_initialized()
    assert path.read_bytes() == original
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT value FROM historical_evidence").fetchone()[0] == "retain-me"

def test_existing_registry_survives_missing_schema(tmp_path, monkeypatch):
    path = tmp_path / "registry.db"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE historical_evidence (value TEXT)")
    monkeypatch.setattr(db, "DB_PATH", path)
    monkeypatch.setattr(db, "SCHEMA_PATH", tmp_path / "missing.sql")
    original = path.read_bytes()
    with pytest.raises(FileNotFoundError):
        db.ensure_db_initialized()
    assert path.exists()
    assert path.read_bytes() == original


@pytest.fixture
def isolated_registry(tmp_path, monkeypatch):
    path = tmp_path / "registry.db"
    monkeypatch.setattr(db, "DB_PATH", path)
    monkeypatch.setattr(db, "SEED_PATH", tmp_path / "absent-seed.sql")
    return path


@pytest.mark.parametrize("contents", [b"", b"corrupt registry: preserve these bytes"])
def test_empty_or_corrupt_registry_is_preserved(isolated_registry, contents):
    isolated_registry.write_bytes(contents)
    with pytest.raises(RuntimeError, match="empty|preserved"):
        db.ensure_db_initialized()
    assert isolated_registry.read_bytes() == contents


def test_sqlite_file_without_application_tables_is_preserved(isolated_registry):
    with sqlite3.connect(isolated_registry) as conn:
        conn.execute("PRAGMA user_version = 12")
    original = isolated_registry.read_bytes()
    with pytest.raises(RuntimeError, match="preserved"):
        db.ensure_db_initialized()
    assert isolated_registry.read_bytes() == original


def _store_historical_document():
    document = {
        "iah_id": "historical-iah-id",
        "type": "PAIR",
        "mode": "LOCAL",
        "protocol_version": "IAHASH-1.2",
        "signature": "historical-signature-must-survive",
        "h_total": "historical-hash-must-survive",
        "store_raw": True,
        "raw_prompt_text": "Historical prompt",
        "raw_response_text": "Historical response",
    }
    db.store_iah_document(document)
    return db.get_iah_document_by_id(document["iah_id"])


def test_repeated_startup_preserves_documents_and_prompts(isolated_registry):
    db.ensure_db_initialized()
    prompt_id = db.create_prompt(
        slug="historical-prompt", title="Historical", full_prompt="Preserve me"
    )
    historical_prompt = db.get_prompt_by_id(prompt_id)
    historical_document = _store_historical_document()

    for _ in range(3):
        db.ensure_db_initialized()
        assert db.get_prompt_by_id(prompt_id) == historical_prompt
        assert db.get_iah_document_by_id("historical-iah-id") == historical_document


def test_migration_failure_keeps_historical_records(isolated_registry):
    # Both required tables exist, but an old/incomplete document schema cannot
    # support the migration's iah_id index. Startup must fail without dropping it.
    with sqlite3.connect(isolated_registry) as conn:
        conn.execute("CREATE TABLE prompts (id INTEGER, full_prompt TEXT)")
        conn.execute("INSERT INTO prompts VALUES (1, 'historical prompt')")
        conn.execute("CREATE TABLE iahash_documents (signature TEXT)")
        conn.execute("INSERT INTO iahash_documents VALUES ('historical signature')")
    with pytest.raises(RuntimeError, match="preserved") as failure:
        db.ensure_db_initialized()
    assert isinstance(failure.value.__cause__, sqlite3.OperationalError)
    with sqlite3.connect(isolated_registry) as conn:
        assert conn.execute("SELECT full_prompt FROM prompts").fetchone() == (
            "historical prompt",
        )
        assert conn.execute("SELECT signature FROM iahash_documents").fetchone() == (
            "historical signature",
        )


def test_seed_error_preserves_existing_document(isolated_registry, tmp_path, monkeypatch):
    db.ensure_db_initialized()
    historical_document = _store_historical_document()
    seed = tmp_path / "broken-seed.sql"
    seed.write_text("INVALID SEED SQL;", encoding="utf-8")
    monkeypatch.setattr(db, "SEED_PATH", seed)
    with pytest.raises(RuntimeError, match="preserved"):
        db.ensure_db_initialized()
    assert db.get_iah_document_by_id("historical-iah-id") == historical_document


def test_sqlite_backup_can_restore_after_failed_startup(isolated_registry, tmp_path):
    db.ensure_db_initialized()
    historical_document = _store_historical_document()
    backup_path = tmp_path / "registry.backup.db"
    with sqlite3.connect(isolated_registry) as original:
        with sqlite3.connect(backup_path) as backup:
            original.backup(backup)
    backup_bytes = backup_path.read_bytes()

    isolated_registry.write_bytes(b"corrupted after backup")
    with pytest.raises(RuntimeError, match="preserved"):
        db.ensure_db_initialized()
    assert isolated_registry.read_bytes() == b"corrupted after backup"
    assert backup_path.read_bytes() == backup_bytes

    # Recovery is an explicit operator action, never automatic startup behavior.
    shutil.copyfile(backup_path, isolated_registry)
    db.ensure_db_initialized()
    assert db.get_iah_document_by_id("historical-iah-id") == historical_document
