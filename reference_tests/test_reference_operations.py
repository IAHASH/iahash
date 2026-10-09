"""Operator mistakes and failed copies must preserve the existing identity/data."""
from contextlib import closing
import sqlite3

import pytest

from iahash_server import __main__ as operations


def test_lost_private_key_does_not_generate_another_identity(tmp_path):
    private, public = tmp_path/'private', tmp_path/'public'
    operations.init_key(private, public)
    expected = public.read_bytes()
    private.unlink()  # Synthetic fixture only.
    with pytest.raises(ValueError):
        operations.init_key(private, public)
    assert not private.exists() and public.read_bytes() == expected


def test_key_mismatch_fails_without_overwrite(tmp_path):
    private, public = tmp_path/'private', tmp_path/'public'
    other, other_public = tmp_path/'other', tmp_path/'other-public'
    operations.init_key(private, public)
    operations.init_key(other, other_public)
    public.write_bytes(other_public.read_bytes())
    expected = private.read_bytes(), public.read_bytes()
    with pytest.raises(ValueError):
        operations.init_key(private, public)
    assert (private.read_bytes(), public.read_bytes()) == expected


def test_backup_never_overwrites_source_or_existing_destination(tmp_path):
    source, output = tmp_path/'source.sqlite', tmp_path/'existing.sqlite'
    with closing(sqlite3.connect(source)) as db:
        db.execute('CREATE TABLE evidence (value TEXT)')
        db.execute("INSERT INTO evidence VALUES ('preserve')")
        db.commit()
    output.write_bytes(b'pre-existing evidence')
    before = source.read_bytes(), output.read_bytes()
    with pytest.raises(FileExistsError):
        operations.backup_database(source, output)
    with pytest.raises(ValueError):
        operations.backup_database(source, source)
    assert (source.read_bytes(), output.read_bytes()) == before


def test_failed_destination_connection_closes_source(tmp_path, monkeypatch):
    source, output = tmp_path/'source.sqlite', tmp_path/'output.sqlite'
    with closing(sqlite3.connect(source)) as db:
        db.execute('CREATE TABLE evidence (value TEXT)')
        db.commit()
    original = operations.sqlite3.connect
    handles = []

    def connect(target, *args, **kwargs):
        if target == output:
            raise sqlite3.OperationalError('Synthetic destination failure')
        connection = original(target, *args, **kwargs)
        handles.append(connection)
        return connection

    monkeypatch.setattr(operations.sqlite3, 'connect', connect)
    with pytest.raises(sqlite3.OperationalError):
        operations.backup_database(source, output)
    with pytest.raises(sqlite3.ProgrammingError):
        handles[0].execute('SELECT 1')
    assert source.exists() and output.exists()
