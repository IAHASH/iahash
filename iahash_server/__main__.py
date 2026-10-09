"""Explicit LAB operations; importing the reference service never creates keys."""
from __future__ import annotations

import argparse
from contextlib import ExitStack, closing
import os
from pathlib import Path
import sqlite3

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def _write_exclusive(path: Path, content: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    with os.fdopen(fd, "wb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def init_key(private_path: Path, public_path: Path) -> None:
    """Create once or recover only the public half; never replace identity."""
    if private_path.resolve() == public_path.resolve():
        raise ValueError("Private and public paths must differ")
    if not private_path.exists():
        if public_path.exists():
            raise ValueError("Private key missing; restore the existing identity")
        key = Ed25519PrivateKey.generate()
        _write_exclusive(private_path, key.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption()), 0o600)
    else:
        key = serialization.load_pem_private_key(private_path.read_bytes(), password=None)
        if not isinstance(key, Ed25519PrivateKey):
            raise ValueError("Private key must be Ed25519")
    expected = key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    if public_path.exists():
        actual = serialization.load_pem_public_key(public_path.read_bytes())
        if actual.public_bytes(serialization.Encoding.DER,
                               serialization.PublicFormat.SubjectPublicKeyInfo) != key.public_key().public_bytes(
                                   serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo):
            raise ValueError("Public/private mismatch")
    else:
        _write_exclusive(public_path, expected, 0o644)
    private_path.chmod(0o600)
    public_path.chmod(0o644)


def backup_database(source: Path, output: Path) -> None:
    """Consistent SQLite backup to a new path, also suitable for isolated restore."""
    if source.resolve() == output.resolve() or not source.is_file():
        raise ValueError("Source must exist and output must be a different new path")
    output.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(fd)
    # A failed operation deliberately preserves its output for diagnosis.
    with ExitStack() as stack:
        src = stack.enter_context(closing(sqlite3.connect(source.resolve().as_uri() + "?mode=ro", uri=True)))
        dst = stack.enter_context(closing(sqlite3.connect(output)))
        if src.execute("PRAGMA integrity_check").fetchone() != ("ok",):
            raise ValueError("Source integrity check failed")
        src.backup(dst)
        dst.commit()
        if dst.execute("PRAGMA integrity_check").fetchone() != ("ok",):
            raise ValueError("Backup integrity check failed")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init-key", help="Explicit creation or public-key recovery")
    init.add_argument("--private", type=Path, required=True)
    init.add_argument("--public", type=Path, required=True)
    for name in ("backup", "restore"):
        copy = commands.add_parser(name, help="Consistent copy to a new path; never replace live DB")
        copy.add_argument("--source", type=Path, required=True)
        copy.add_argument("--output", type=Path, required=True)
    serve = commands.add_parser("serve")
    serve.add_argument("--db", type=Path, required=True)
    serve.add_argument("--private", type=Path, required=True)
    serve.add_argument("--issuer-id", required=True)
    serve.add_argument("--environment", choices=["LAB", "STAGING", "PRODUCTION"], required=True)
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if args.command == "init-key":
        init_key(args.private, args.public)
    elif args.command in {"backup", "restore"}:
        backup_database(args.source, args.output)
    else:
        token = os.environ.get("IAHASH_API_TOKEN", "")
        if len(token) < 32:
            parser.error("IAHASH_API_TOKEN must contain at least 32 characters")
        key = serialization.load_pem_private_key(args.private.read_bytes(), password=None)
        if not isinstance(key, Ed25519PrivateKey):
            parser.error("Private key must be Ed25519")
        from iahash_server.app import create_app
        import uvicorn
        app = create_app(db_path=args.db, private_key=key,
                         issuer_id=args.issuer_id, environment=args.environment,
                         api_token=token)
        uvicorn.run(app, host=args.host, port=args.port, access_log=False)


if __name__ == "__main__":
    main()
