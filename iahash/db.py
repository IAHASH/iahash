# iahash/db.py
"""
SQLite helpers for IA-HASH v1.2.

- Usa la base de datos db/iahash.db (misma ruta que start.sh).
- Expone store_iah_document(document) para que issuer.py persista los documentos.
- Es tolerante a cambios futuros de schema: detecta dinámicamente las columnas
  disponibles en iahash_documents y solo inserta las que existan.
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, Optional


# ============================================================================
# Paths & conexión
# ============================================================================

# BASE_DIR = raíz del proyecto (donde están api/, iahash/, db/, start.sh)
BASE_DIR = Path(__file__).resolve().parent.parent

# Permite sobreescribir la ruta de la DB vía env si algún día lo necesitas
DB_PATH = Path(os.getenv("IAHASH_DB_PATH", BASE_DIR / "db" / "iahash.db"))


def _get_connection() -> sqlite3.Connection:
    """
    Crea una nueva conexión SQLite.

    Se usa una conexión corta por operación (pattern sencillo y suficiente
    para el tráfico esperado de IA-HASH v1.2).
    """
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def db_conn() -> Iterator[sqlite3.Connection]:
    conn = _get_connection()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


# ============================================================================
# Utilidades internas
# ============================================================================

def _get_table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    """
    Devuelve el conjunto de nombres de columnas de una tabla.

    Esto nos permite insertar solo las columnas que existan realmente,
    haciendo el código tolerante a cambios de schema (por ejemplo,
    si todavía no has actualizado schema.sql en producción).
    """
    cur = conn.execute(f"PRAGMA table_info({table})")
    return {row["name"] for row in cur.fetchall()}


# ============================================================================
# API pública
# ============================================================================

def store_iah_document(document: Dict[str, Any]) -> Optional[int]:
    """
    Inserta un documento IA-HASH en la tabla iahash_documents.

    Espera un dict en el formato que construye iahash.issuer._issue_document,
    por ejemplo:

        {
            "iah_id": "...",
            "prompt_id": ...,
            "type": "PAIR" | "CONVERSATION",
            "mode": "LOCAL" | "TRUSTED_URL",
            "prompt_hmac_verified": bool,
            "protocol_version": "...",
            "model": "...",
            "timestamp": "...",
            "h_prompt": "...",
            "h_response": "...",
            "h_total": "...",
            "issuer_id": "...",
            "issuer_pk_url": "...",
            "signature": "...",
            "conversation_url": "...",
            "provider": "...",
            "subject_id": "...",
            "store_raw": bool,
            "raw_prompt_text": "...",
            "raw_response_text": "...",
            # opcionales:
            "raw_context_text": "...",
            ...
        }

    Además, este helper serializa el documento completo a JSON y lo guarda
    en la columna json_document si existe (opción B).
    """
    # json_document: document completo en bruto, para auditoría futura
    json_document = json.dumps(document, ensure_ascii=False, separators=(",", ":"))

    with db_conn() as conn:
        cols = _get_table_columns(conn, "iahash_documents")

        base_data: Dict[str, Any] = {
            "iah_id": document.get("iah_id"),
            "prompt_id": document.get("prompt_id"),
            "type": document.get("type"),
            "mode": document.get("mode"),
            "prompt_hmac_verified": int(bool(document.get("prompt_hmac_verified"))),
            "protocol_version": document.get("protocol_version"),
            "model": document.get("model"),
            "timestamp": document.get("timestamp"),
            "h_prompt": document.get("h_prompt"),
            "h_response": document.get("h_response"),
            "h_total": document.get("h_total"),
            "issuer_id": document.get("issuer_id"),
            "issuer_pk_url": document.get("issuer_pk_url"),
            "signature": document.get("signature"),
            "conversation_url": document.get("conversation_url"),
            "provider": document.get("provider"),
            "subject_id": document.get("subject_id"),
            "store_raw": int(bool(document.get("store_raw"))),
            "raw_prompt_text": document.get("raw_prompt_text"),
            "raw_response_text": document.get("raw_response_text"),
            # campos opcionales de esquema v1.2 extendido:
            "raw_context_text": document.get("raw_context_text"),
            "json_document": json_document,
        }

        # Filtramos solo las columnas que existan realmente
        data = {k: v for k, v in base_data.items() if k in cols}

        if not data:
            # Algo muy raro: tabla sin columnas esperadas
            return None

        column_names = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))
        values = list(data.values())

        sql = f"INSERT INTO iahash_documents ({column_names}) VALUES ({placeholders})"
        cur = conn.execute(sql, values)
        return cur.lastrowid
