"""SQLite helpers for IA-HASH v1.2."""

from __future__ import annotations

import sqlite3
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "db" / "iahash.db"
SCHEMA_PATH = BASE_DIR / "db" / "schema.sql"
SEED_PATH = BASE_DIR / "db" / "seed_prompts.sql"


def ensure_db_initialized() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        return

    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema file missing: {SCHEMA_PATH}")

    subprocess.run(["sqlite3", str(DB_PATH)], input=SCHEMA_PATH.read_bytes(), check=True)
    if SEED_PATH.exists():
        subprocess.run(["sqlite3", str(DB_PATH)], input=SEED_PATH.read_bytes(), check=True)


ensure_db_initialized()


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_prompt_by_slug(slug: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            SELECT id, slug, owner_id, title, description, full_prompt, category, is_master, visibility,
                   h_public, h_secret, signature_prompt, created_at, updated_at
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
            SELECT id, slug, owner_id, title, description, category, is_master, visibility, created_at, updated_at
            FROM prompts
            ORDER BY category, slug
            """
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def store_iah_document(document: Dict[str, Any]) -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO iahash_documents (
                iah_id, prompt_id, type, mode, prompt_hmac_verified, protocol_version, model, timestamp,
                h_prompt, h_response, h_total, issuer_id, issuer_pk_url, signature,
                conversation_url, provider, subject_id, store_raw, raw_prompt_text, raw_response_text, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """,
            (
                document.get("iah_id"),
                document.get("prompt_id"),
                document.get("type"),
                document.get("mode"),
                1 if document.get("prompt_hmac_verified") else 0,
                document.get("protocol_version"),
                document.get("model"),
                document.get("timestamp"),
                document.get("h_prompt"),
                document.get("h_response"),
                document.get("h_total"),
                document.get("issuer_id"),
                document.get("issuer_pk_url"),
                document.get("signature"),
                document.get("conversation_url"),
                document.get("provider"),
                document.get("subject_id"),
                1 if document.get("store_raw") else 0,
                document.get("raw_prompt_text") if document.get("store_raw") else None,
                document.get("raw_response_text") if document.get("store_raw") else None,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def get_iah_document_by_id(iah_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            SELECT * FROM iahash_documents WHERE iah_id = ?
            """,
            (iah_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_sequences() -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        sequences = [dict(r) for r in conn.execute("SELECT * FROM sequences ORDER BY created_at DESC").fetchall()]
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
        SELECT ss.id, ss.position, ss.title, ss.description, ss.prompt_id, p.slug as prompt_slug
        FROM sequence_steps ss
        LEFT JOIN prompts p ON ss.prompt_id = p.id
        WHERE ss.sequence_id = ?
        ORDER BY ss.position ASC
        """,
        (sequence_id,),
    )
    return [dict(r) for r in cur.fetchall()]
