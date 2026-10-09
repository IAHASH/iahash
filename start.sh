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

KEY_DIR="/data/keys"
DB_DIR="$SCRIPT_DIR/db"
DB_PATH="$DB_DIR/iahash.db"

mkdir -p "$KEY_DIR"
mkdir -p "$DB_DIR"

# ---------------------------------------------------------------------------
# GENERACIÓN DE CLAVES (solo si no existen)
# ---------------------------------------------------------------------------

python3 - <<'PY'
import os
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

root = Path("/data/keys")
private_path = root / "issuer_ed25519.private"
public_path = root / "issuer_ed25519.pub"
if not private_path.exists():
    if public_path.exists():
        raise SystemExit("Private key missing: refusing to replace issuer identity")
    if os.getenv("IAHASH_ALLOW_KEY_INITIALIZATION") != "1":
        raise SystemExit("Explicit IAHASH_ALLOW_KEY_INITIALIZATION=1 required")
    key = Ed25519PrivateKey.generate()
    private_path.write_bytes(key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption()))
else:
    key = serialization.load_pem_private_key(private_path.read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise SystemExit("Issuer private key is not Ed25519")
private_path.chmod(0o600)
expected = key.public_key().public_bytes(
    serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
if public_path.exists() and public_path.read_bytes() != expected:
    raise SystemExit("Issuer public/private keys mismatch")
if not public_path.exists():
    public_path.write_bytes(expected)
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
