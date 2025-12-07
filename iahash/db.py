"""SQLite helpers for IA-HASH v1.2."""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "db" / "iahash.db"
SCHEMA_PATH = BASE_DIR / "db" / "schema.sql"
SEED_PATH = BASE_DIR / "db" / "seed_prompts.sql"

logger = logging.getLogger(__name__)


def ensure_db_initialized() -> None:
    """
    Si no existe la base de datos, crea el fichero y aplica:
      - schema.sql
      - seed_prompts.sql (si existe)

    Ojo: start.sh ya hace esto también en el arranque del contenedor.
    Aquí es solo una red de seguridad para ejecuciones fuera de Docker.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    needs_bootstrap = not DB_PATH.exists() or DB_PATH.stat().st_size == 0

    if not needs_bootstrap:
        try:
            conn = sqlite3.connect(str(DB_PATH))
            cur = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            existing_tables = {row[0] for row in cur.fetchall()}
            needs_bootstrap = not {"prompts", "iahash_documents"}.issubset(
                existing_tables
            )
        except Exception:
            needs_bootstrap = True
        finally:
            try:
                conn.close()
            except Exception:
                pass

    if not needs_bootstrap:
        return

    if DB_PATH.exists():
        DB_PATH.unlink(missing_ok=True)

    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema file missing: {SCHEMA_PATH}")

    try:
        conn = sqlite3.connect(str(DB_PATH))
        try:
            conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
            if SEED_PATH.exists():
                conn.executescript(SEED_PATH.read_text(encoding="utf-8"))
            conn.commit()
        finally:
            conn.close()
    except Exception as exc:
        logger.exception("Failed to initialize database at %s", DB_PATH)
        if DB_PATH.exists():
            try:
                DB_PATH.unlink()
            except OSError:
                logger.warning("Could not clean up partial database at %s", DB_PATH)
        raise RuntimeError("Failed to initialize database") from exc


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# PROMPTS
# ---------------------------------------------------------------------------

def get_prompt_by_slug(slug: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            SELECT id, slug, owner_id, title, description, full_prompt, category,
                   is_master, visibility,
                   h_public, h_secret, signature_prompt,
                   created_at, updated_at
            FROM prompts
            WHERE slug = ?
            """,
            (slug,),
        )
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_prompts() -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            SELECT id, slug, owner_id, title, description, category,
                   is_master, visibility, created_at, updated_at
            FROM prompts
            ORDER BY category, slug
            """
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# IA-HASH DOCUMENTS
# ---------------------------------------------------------------------------

def _get_table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    """
    Devuelve el conjunto de nombres de columnas de una tabla.
    Útil para hacer inserts tolerantes a cambios de schema.
    """
    cur = conn.execute(f"PRAGMA table_info({table})")
    return {row["name"] for row in cur.fetchall()}


def store_iah_document(document: Dict[str, Any]) -> None:
    """
    Inserta un documento IA-HASH en iahash_documents.

    Usa las columnas del schema v1.2 (opción B):

      iah_id, prompt_id, type, mode, prompt_hmac_verified,
      protocol_version, model, timestamp,
      h_prompt, h_response, h_total,
      issuer_id, issuer_pk_url, signature,
      conversation_url, provider, subject_id,
      store_raw, raw_prompt_text, raw_response_text,
      raw_context_text, json_document

    y solo inserta las columnas que realmente existan en la tabla,
    para no romper si el schema no está aún actualizado en algún entorno.
    """
    # Documento completo serializado (para json_document)
    json_doc = json.dumps(
        document,
        ensure_ascii=False,
        separators=(",", ":"),
    )

    conn = get_connection()
    try:
        cols = _get_table_columns(conn, "iahash_documents")

        base_data: Dict[str, Any] = {
            "iah_id": document.get("iah_id"),
            "prompt_id": document.get("prompt_id"),
            "type": document.get("type"),
            "mode": document.get("mode"),
            "prompt_hmac_verified": 1 if document.get("prompt_hmac_verified") else 0,
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
            "store_raw": 1 if document.get("store_raw") else 0,
            "raw_prompt_text": (
                document.get("raw_prompt_text")
                if document.get("store_raw")
                else None
            ),
            "raw_response_text": (
                document.get("raw_response_text")
                if document.get("store_raw")
                else None
            ),
            # campos nuevos del schema v1.2 opción B
            "raw_context_text": document.get("raw_context_text"),
            "json_document": json_doc,
        }

        # Filtramos solo lo que exista realmente como columna
        data = {k: v for k, v in base_data.items() if k in cols}

        if not data:
            # Si esto pasa, algo va muy mal con el schema
            raise RuntimeError("iahask_documents no tiene columnas esperadas")

        column_names = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))
        values = list(data.values())

        conn.execute(
            f"""
            INSERT INTO iahash_documents ({column_names})
            VALUES ({placeholders})
            """,
            values,
        )
        conn.commit()
    finally:
        conn.close()


def get_iah_document_by_id(iah_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            SELECT *
            FROM iahash_documents
            WHERE iah_id = ?
            """,
            (iah_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# SECUENCIAS
# ---------------------------------------------------------------------------

def list_sequences() -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        sequences = [
            dict(r)
            for r in conn.execute(
                "SELECT * FROM sequences ORDER BY created_at DESC"
            ).fetchall()
        ]
        for seq in sequences:
            seq["steps"] = get_sequence_steps(conn, seq["id"])
        return sequences
    finally:
        conn.close()


def get_sequence_by_slug(slug: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        cur = conn.execute("SELECT * FROM sequences WHERE slug = ?", (slug,))
        row = cur.fetchone()
        if not row:
            return None
        sequence = dict(row)
        sequence["steps"] = get_sequence_steps(conn, sequence["id"])
        return sequence
    finally:
        conn.close()


def get_sequence_steps(conn: sqlite3.Connection, sequence_id: int) -> List[Dict[str, Any]]:
    cur = conn.execute(
        """
        SELECT ss.id, ss.position, ss.title, ss.description, ss.prompt_id,
               p.slug as prompt_slug
        FROM sequence_steps ss
        LEFT JOIN prompts p ON ss.prompt_id = p.id
        WHERE ss.sequence_id = ?
        ORDER BY ss.position ASC
        """,
        (sequence_id,),
    )
    return [dict(r) for r in cur.fetchall()]
