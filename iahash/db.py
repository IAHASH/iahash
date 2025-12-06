# iahash/db.py
# Qué/por qué: utilidades simples para acceder a SQLite (prompts) desde el código IA-HASH

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "db" / "iahash.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_prompt_by_slug(slug: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            SELECT id, slug, code, category, title, short_description, body, version, enabled,
                   created_at, updated_at
            FROM prompts
            WHERE slug = ? AND enabled = 1
            """,
            (slug,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return dict(row)
    finally:
        conn.close()


def list_prompts() -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            SELECT id, slug, code, category, title, short_description, version, enabled
            FROM prompts
            ORDER BY category, slug
            """
        )
        rows = cur.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
