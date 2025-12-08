"""SQLite helpers for IA-HASH v1.2."""

from __future__ import annotations

import hmac
import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from iahash.crypto import normalize_text, sha256_hex

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "db" / "iahash.db"
SCHEMA_PATH = BASE_DIR / "db" / "schema.sql"
SEED_PATH = BASE_DIR / "db" / "seed_prompts.sql"

logger = logging.getLogger(__name__)


def ensure_db_initialized() -> None:
    """
    Garantiza que la base de datos existe y está actualizada:

      - Si falta, se crea aplicando schema.sql.
      - Si ya existe, aplica migraciones ligeras para columnas/índices nuevos.
      - Siempre carga seed_prompts.sql si existe y la tabla prompts está vacía.

    Ojo: start.sh ya hace esto también en el arranque del contenedor.
    Aquí es solo una red de seguridad para ejecuciones fuera de Docker.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    needs_bootstrap = not DB_PATH.exists() or DB_PATH.stat().st_size == 0

    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(f"Schema file missing: {SCHEMA_PATH}")

    conn: Optional[sqlite3.Connection] = None

    try:
        if needs_bootstrap:
            conn = sqlite3.connect(str(DB_PATH))
        else:
            try:
                conn = sqlite3.connect(str(DB_PATH))
                cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                existing_tables = {row[0] for row in cur.fetchall()}
                needs_bootstrap = not {"prompts", "iahash_documents"}.issubset(
                    existing_tables
                )
            except Exception:
                if conn:
                    conn.close()
                raise

        if needs_bootstrap and DB_PATH.exists():
            conn.close()
            DB_PATH.unlink(missing_ok=True)
            conn = sqlite3.connect(str(DB_PATH))

        if conn is None:
            raise RuntimeError("Database connection could not be established")

        _apply_schema(conn, bootstrap=needs_bootstrap)
        _load_seed_data(conn)
        conn.commit()
    except Exception as exc:
        logger.exception("Failed to initialize database at %s", DB_PATH)
        if DB_PATH.exists():
            try:
                DB_PATH.unlink()
            except OSError:
                logger.warning("Could not clean up partial database at %s", DB_PATH)
        raise RuntimeError("Failed to initialize database") from exc
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass


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


def get_prompt_by_id(prompt_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            SELECT id, slug, owner_id, title, description, full_prompt, category,
                   is_master, visibility,
                   h_public, h_secret, signature_prompt,
                   created_at, updated_at
            FROM prompts
            WHERE id = ?
            """,
            (prompt_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_prompts(*, visibility: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        where_clause = ""
        params: Tuple[Any, ...] = ()
        if visibility:
            where_clause = "WHERE visibility = ?"
            params = (visibility,)

        cur = conn.execute(
            f"""
            SELECT id, slug, owner_id, title, description, category,
                   is_master, visibility, h_public, created_at, updated_at
            FROM prompts
            {where_clause}
            ORDER BY category, slug
            """,
            params,
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def _compute_prompt_hashes(
    full_prompt: str, *, hmac_key: Optional[str]
) -> Tuple[str, Optional[str]]:
    normalized = normalize_text(full_prompt)
    h_public = sha256_hex(normalized.encode("utf-8"))

    h_secret: Optional[str] = None
    if hmac_key:
        h_secret = hmac.new(
            hmac_key.encode("utf-8"), normalized.encode("utf-8"), "sha256"
        ).hexdigest()
    return h_public, h_secret


def create_prompt(
    *,
    slug: str,
    title: str,
    full_prompt: str,
    description: Optional[str] = None,
    owner_id: Optional[str] = None,
    category: Optional[str] = None,
    is_master: bool = True,
    visibility: str = "public",
    signature_prompt: Optional[str] = None,
    h_public: Optional[str] = None,
    h_secret: Optional[str] = None,
) -> int:
    """
    Inserta un prompt maestro e incluye sus hashes público y privado.
    Devuelve el ID autoincremental creado.
    """

    hmac_key = os.getenv("IAHASH_PROMPT_HMAC_KEY")
    computed_public, computed_secret = _compute_prompt_hashes(
        full_prompt, hmac_key=hmac_key
    )

    final_h_public = h_public or computed_public
    final_h_secret = h_secret or computed_secret

    conn = get_connection()
    try:
        cols = _get_table_columns(conn, "prompts")
        now = datetime.now(timezone.utc).isoformat()
        data: Dict[str, Any] = {
            "slug": slug,
            "owner_id": owner_id,
            "title": title,
            "description": description,
            "full_prompt": full_prompt,
            "category": category,
            "is_master": 1 if is_master else 0,
            "visibility": visibility,
            "h_public": final_h_public,
            "h_secret": final_h_secret,
            "signature_prompt": signature_prompt,
            "created_at": now,
            "updated_at": now,
        }

        filtered = {k: v for k, v in data.items() if k in cols}
        col_names = ", ".join(filtered.keys())
        placeholders = ", ".join(["?"] * len(filtered))
        values = list(filtered.values())

        conn.execute(
            f"INSERT INTO prompts ({col_names}) VALUES ({placeholders})",
            values,
        )
        conn.commit()
        return int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])
    finally:
        conn.close()


def update_prompt(
    prompt_id: int,
    *,
    title: Optional[str] = None,
    description: Optional[str] = None,
    full_prompt: Optional[str] = None,
    category: Optional[str] = None,
    visibility: Optional[str] = None,
    signature_prompt: Optional[str] = None,
    h_public: Optional[str] = None,
    h_secret: Optional[str] = None,
) -> None:
    """Actualiza un prompt maestro, recalculando hashes si cambia el texto."""

    existing = get_prompt_by_id(prompt_id)
    if not existing:
        raise ValueError(f"Prompt with id {prompt_id} not found")

    prompt_text = (
        full_prompt if full_prompt is not None else existing.get("full_prompt", "")
    )
    hmac_key = os.getenv("IAHASH_PROMPT_HMAC_KEY")
    computed_public, computed_secret = _compute_prompt_hashes(
        prompt_text, hmac_key=hmac_key
    )

    final_h_public = h_public or computed_public
    final_h_secret = h_secret or computed_secret

    conn = get_connection()
    try:
        cols = _get_table_columns(conn, "prompts")
        updates: Dict[str, Any] = {
            "title": title if title is not None else existing.get("title"),
            "description": (
                description if description is not None else existing.get("description")
            ),
            "full_prompt": prompt_text,
            "category": category if category is not None else existing.get("category"),
            "visibility": (
                visibility if visibility is not None else existing.get("visibility")
            ),
            "signature_prompt": (
                signature_prompt
                if signature_prompt is not None
                else existing.get("signature_prompt")
            ),
            "h_public": final_h_public,
            "h_secret": final_h_secret,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        filtered = {k: v for k, v in updates.items() if k in cols}
        assignments = ", ".join([f"{k} = ?" for k in filtered.keys()])

        conn.execute(
            f"UPDATE prompts SET {assignments} WHERE id = ?",
            [*filtered.values(), prompt_id],
        )
        conn.commit()
    finally:
        conn.close()


def delete_prompt(prompt_id: int) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM prompts WHERE id = ?", (prompt_id,))
        conn.commit()
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
    columns = set()
    for row in cur.fetchall():
        try:
            columns.add(row["name"])
        except Exception:
            # Fallback para conexiones sin row_factory
            columns.add(row[1])
    return columns


def _apply_schema(conn: sqlite3.Connection, *, bootstrap: bool) -> None:
    """Aplica el schema inicial o actualizaciones incrementales."""
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")

    if bootstrap:
        conn.executescript(schema_sql)
        return

    # Actualizaciones mínimas para entornos con schema antiguo
    prompt_cols = _get_table_columns(conn, "prompts")
    if "h_public" not in prompt_cols:
        conn.execute("ALTER TABLE prompts ADD COLUMN h_public TEXT")
    if "h_secret" not in prompt_cols:
        conn.execute("ALTER TABLE prompts ADD COLUMN h_secret TEXT")

    cols = _get_table_columns(conn, "iahash_documents")
    if "raw_context_text" not in cols:
        conn.execute("ALTER TABLE iahash_documents ADD COLUMN raw_context_text TEXT")
    if "json_document" not in cols:
        conn.execute("ALTER TABLE iahash_documents ADD COLUMN json_document TEXT")

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_iah_documents_iah_id"
        " ON iahash_documents(iah_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_iah_documents_prompt_id"
        " ON iahash_documents(prompt_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_iah_documents_created_at"
        " ON iahash_documents(created_at)"
    )

    sequence_cols = _get_table_columns(conn, "sequences")
    if "updated_at" not in sequence_cols:
        conn.execute("ALTER TABLE sequences ADD COLUMN updated_at TEXT")

    step_cols = _get_table_columns(conn, "sequence_steps")
    if "updated_at" not in step_cols:
        conn.execute("ALTER TABLE sequence_steps ADD COLUMN updated_at TEXT")


def _load_seed_data(conn: sqlite3.Connection) -> None:
    """Carga seed_prompts.sql si existe y aún no hay prompts."""
    if not SEED_PATH.exists():
        logger.info("Seed file not found: %s", SEED_PATH)
        return

    try:
        cur = conn.execute("SELECT COUNT(*) FROM prompts")
        prompt_count = cur.fetchone()[0]
    except sqlite3.Error:
        logger.warning("Unable to count prompts; attempting to load seed data anyway")
        prompt_count = 0

    if prompt_count:
        logger.info(
            "Seed de prompts omitido: la tabla ya contiene %s filas", prompt_count
        )
        return

    try:
        conn.executescript(SEED_PATH.read_text(encoding="utf-8"))
        logger.info("Seed data loaded from %s", SEED_PATH)
    except Exception:
        logger.exception("Failed to load seed data from %s", SEED_PATH)
        raise


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
                document.get("raw_prompt_text") if document.get("store_raw") else None
            ),
            "raw_response_text": (
                document.get("raw_response_text") if document.get("store_raw") else None
            ),
            # campos nuevos del schema v1.2 opción B
            "raw_context_text": (
                document.get("raw_context_text") if document.get("store_raw") else None
            ),
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


def _insert_sequence_steps(
    conn: sqlite3.Connection, sequence_id: int, steps: List[Dict[str, Any]]
) -> None:
    """Inserta los pasos de una secuencia asegurando orden estable."""

    step_cols = _get_table_columns(conn, "sequence_steps")
    now = datetime.now(timezone.utc).isoformat()

    for position, step in enumerate(steps, start=1):
        payload = {
            "sequence_id": sequence_id,
            "position": step.get("position") or position,
            "title": step["title"],
            "description": step.get("description"),
            "prompt_id": step.get("prompt_id"),
            "created_at": now,
            "updated_at": now,
        }

        filtered = {k: v for k, v in payload.items() if k in step_cols}
        columns = ", ".join(filtered.keys())
        placeholders = ", ".join(["?"] * len(filtered))
        conn.execute(
            f"INSERT INTO sequence_steps ({columns}) VALUES ({placeholders})",
            list(filtered.values()),
        )


def create_sequence(
    *,
    slug: str,
    title: str,
    description: Optional[str] = None,
    category: Optional[str] = None,
    visibility: str = "public",
    steps: Optional[List[Dict[str, Any]]] = None,
) -> int:
    """Crea una secuencia y sus pasos en una transacción única."""

    conn = get_connection()
    try:
        cols = _get_table_columns(conn, "sequences")
        now = datetime.now(timezone.utc).isoformat()
        base_data = {
            "slug": slug,
            "title": title,
            "description": description,
            "category": category,
            "visibility": visibility,
            "created_at": now,
            "updated_at": now,
        }

        filtered = {k: v for k, v in base_data.items() if k in cols}
        column_names = ", ".join(filtered.keys())
        placeholders = ", ".join(["?"] * len(filtered))

        conn.execute(
            f"INSERT INTO sequences ({column_names}) VALUES ({placeholders})",
            list(filtered.values()),
        )
        seq_id = int(conn.execute("SELECT last_insert_rowid()").fetchone()[0])

        if steps:
            _insert_sequence_steps(conn, seq_id, steps)

        conn.commit()
        return seq_id
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise ValueError("Sequence with same slug already exists") from exc
    finally:
        conn.close()


def update_sequence(
    sequence_id: int,
    *,
    title: Optional[str] = None,
    description: Optional[str] = None,
    category: Optional[str] = None,
    visibility: Optional[str] = None,
    steps: Optional[List[Dict[str, Any]]] = None,
) -> None:
    """Actualiza metadatos y pasos. Los pasos se sustituyen si se incluyen."""

    conn = get_connection()
    try:
        cols = _get_table_columns(conn, "sequences")
        cur = conn.execute("SELECT * FROM sequences WHERE id = ?", (sequence_id,))
        existing = cur.fetchone()
        if not existing:
            raise ValueError(f"Sequence with id {sequence_id} not found")

        payload = {
            "title": title if title is not None else existing["title"],
            "description": (
                description if description is not None else existing["description"]
            ),
            "category": category if category is not None else existing["category"],
            "visibility": (
                visibility if visibility is not None else existing["visibility"]
            ),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        filtered = {k: v for k, v in payload.items() if k in cols}
        assignments = ", ".join([f"{k} = ?" for k in filtered.keys()])

        conn.execute(
            f"UPDATE sequences SET {assignments} WHERE id = ?",
            [*filtered.values(), sequence_id],
        )

        if steps is not None:
            conn.execute(
                "DELETE FROM sequence_steps WHERE sequence_id = ?", (sequence_id,)
            )
            _insert_sequence_steps(conn, sequence_id, steps)

        conn.commit()
    finally:
        conn.close()


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


def get_sequence_steps(
    conn: sqlite3.Connection, sequence_id: int
) -> List[Dict[str, Any]]:
    cur = conn.execute(
        """
        SELECT ss.id, ss.position, ss.title, ss.description, ss.prompt_id,
               ss.updated_at, p.slug as prompt_slug, p.title as prompt_title,
               p.full_prompt as prompt_text
        FROM sequence_steps ss
        LEFT JOIN prompts p ON ss.prompt_id = p.id
        WHERE ss.sequence_id = ?
        ORDER BY ss.position ASC
        """,
        (sequence_id,),
    )
    return [dict(r) for r in cur.fetchall()]
