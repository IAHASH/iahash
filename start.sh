#!/bin/sh
set -e

echo "=========================================="
echo "        IA-HASH v1.2 – Startup"
echo "=========================================="

SCRIPT_DIR="$(cd -- "$(dirname "$0")" && pwd)"

# ---------------------------------------------------------------------------
# DIRECTORIOS IMPORTANTES
# ---------------------------------------------------------------------------

KEY_DIR="/data/keys"
DB_DIR="$SCRIPT_DIR/db"
DB_PATH="$DB_DIR/iahash.db"
SCHEMA_FILE="$DB_DIR/schema.sql"
SEED_FILE="$DB_DIR/seed_prompts.sql"

mkdir -p "$KEY_DIR"
mkdir -p "$DB_DIR"

# ---------------------------------------------------------------------------
# GENERACIÓN DE CLAVES (solo si no existen)
# ---------------------------------------------------------------------------

if [ ! -f "$KEY_DIR/issuer_ed25519.private" ] || [ ! -f "$KEY_DIR/issuer_ed25519.pub" ]; then
  echo "[IA-HASH] No keypair found. Generating Ed25519 keypair..."

  python3 - <<'PY'
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

key_dir = Path("/data/keys")
key_dir.mkdir(parents=True, exist_ok=True)

priv = key_dir / "issuer_ed25519.private"
pub = key_dir / "issuer_ed25519.pub"

private_key = Ed25519PrivateKey.generate()
priv.write_bytes(
    private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
)

public_key = private_key.public_key()
pub.write_bytes(
    public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
)

print(f"[IA-HASH] Keys generated at: {key_dir}")
PY

else
  echo "[IA-HASH] Existing keys found. Skipping generation."
fi

# ---------------------------------------------------------------------------
# BASE DE DATOS SQLITE
# ---------------------------------------------------------------------------

if [ ! -f "$DB_PATH" ]; then
  echo "[IA-HASH] Creating SQLite database..."
  sqlite3 "$DB_PATH" < "$SCHEMA_FILE"

  if [ -f "$SEED_FILE" ]; then
    echo "[IA-HASH] Loading initial seed data..."
    sqlite3 "$DB_PATH" < "$SEED_FILE"
  fi
else
  echo "[IA-HASH] Database already exists: $DB_PATH"
fi

# ---------------------------------------------------------------------------
# PYTHONPATH para que FastAPI encuentre los módulos
# ---------------------------------------------------------------------------

export PYTHONPATH="$SCRIPT_DIR"

# ---------------------------------------------------------------------------
# ARRANQUE DEL SERVIDOR
# ---------------------------------------------------------------------------

echo "[IA-HASH] Starting API server..."
exec uvicorn api.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --log-level info
