#!/bin/sh
set -e

echo "=========================================="
echo "        IA-HASH v1.2 – Startup"
echo "=========================================="

SCRIPT_DIR="$(cd -- "$(dirname "$0")" && pwd)"

# ---------------------------------------------------------------------------
# PYTHONPATH para que FastAPI encuentre los módulos
# ---------------------------------------------------------------------------

export PYTHONPATH="$SCRIPT_DIR"

# ---------------------------------------------------------------------------
# DIRECTORIOS IMPORTANTES
# ---------------------------------------------------------------------------

DB_DIR="$SCRIPT_DIR/db"
DB_PATH="$DB_DIR/iahash.db"

mkdir -p "$DB_DIR"

# ---------------------------------------------------------------------------
# GENERACIÓN DE CLAVES (solo si no existen)
# ---------------------------------------------------------------------------

python3 - <<'PY'
import os
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from iahash.crypto import get_default_private_key_path, get_default_public_key_path

private_path = get_default_private_key_path()
public_path = get_default_public_key_path()


def write_new_key(path, data, mode):
    path.parent.mkdir(parents=True, exist_ok=True)
    # Create with final permissions and never replace a concurrently created key.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


if not private_path.exists():
    if public_path.exists():
        raise SystemExit("Private key missing: refusing to replace issuer identity")
    if os.getenv("IAHASH_ALLOW_KEY_INITIALIZATION") != "1":
        raise SystemExit("Explicit IAHASH_ALLOW_KEY_INITIALIZATION=1 required")
    key = Ed25519PrivateKey.generate()
    write_new_key(private_path, key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption()), 0o600)
else:
    key = serialization.load_pem_private_key(private_path.read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise SystemExit("Issuer private key is not Ed25519")
private_path.chmod(0o600)
expected = key.public_key().public_bytes(
    serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
if public_path.exists():
    if public_path.read_bytes() != expected:
        raise SystemExit("Issuer public/private keys mismatch")
else:
    write_new_key(public_path, expected, 0o644)
public_path.chmod(0o644)
print("[IA-HASH] Issuer identity validated")
PY

# ---------------------------------------------------------------------------
# BASE DE DATOS SQLITE (sin binario externo)
# ---------------------------------------------------------------------------

echo "[IA-HASH] Preparing SQLite database..."
python3 - <<'PY'
from iahash.db import ensure_db_initialized, DB_PATH

try:
    ensure_db_initialized()
    print(f"[IA-HASH] Database ready at: {DB_PATH}")
except Exception as exc:  # pragma: no cover - startup script
    print(f"[IA-HASH] Failed to initialize database: {exc}")
    raise
PY

# ---------------------------------------------------------------------------
# ARRANQUE DEL SERVIDOR
# ---------------------------------------------------------------------------

echo "[IA-HASH] Starting API server..."
exec uvicorn api.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --log-level info
