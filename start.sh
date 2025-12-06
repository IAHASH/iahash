#!/bin/sh
set -e

SCRIPT_DIR="$(cd -- "$(dirname "$0")" && pwd)"
KEY_DIR="/data/keys"
DB_PATH="$SCRIPT_DIR/db/iahash.db"
SCHEMA_FILE="$SCRIPT_DIR/db/schema.sql"
SEED_FILE="$SCRIPT_DIR/db/seed_prompts.sql"

mkdir -p "$KEY_DIR"

if [ ! -f "$KEY_DIR/issuer_ed25519.private" ] || [ ! -f "$KEY_DIR/issuer_ed25519.pub" ]; then
  echo "[IA-HASH] Generating Ed25519 keypair..."
  python - <<'PY'
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

key_dir = Path("/data/keys")
priv_path = key_dir / "issuer_ed25519.private"
pub_path = key_dir / "issuer_ed25519.pub"
key_dir.mkdir(parents=True, exist_ok=True)
private_key = Ed25519PrivateKey.generate()
priv_bytes = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
)
priv_path.write_bytes(priv_bytes)
public_key = private_key.public_key()
pub_bytes = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
)
pub_path.write_bytes(pub_bytes)
print(f"[IA-HASH] Keys written to {key_dir}")
PY
fi

if [ ! -f "$DB_PATH" ]; then
  echo "[IA-HASH] Initialising database..."
  sqlite3 "$DB_PATH" < "$SCHEMA_FILE"
  if [ -f "$SEED_FILE" ]; then
    sqlite3 "$DB_PATH" < "$SEED_FILE"
  fi
fi

export PYTHONPATH="$SCRIPT_DIR"

echo "[IA-HASH] Starting API server..."
uvicorn api.main:app --host 0.0.0.0 --port 8000
