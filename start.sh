#!/bin/sh
set -e

SCRIPT_DIR="$(cd -- "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -f "keys/iah_sk.pem" ] || [ ! -f "keys/iah_pk.pem" ]; then
  echo "[IA-HASH] No keys found, generating..."
  python scripts/generate_keys.py
fi

echo "[IA-HASH] Starting API server..."
uvicorn api.main:app --host 0.0.0.0 --port 8000
