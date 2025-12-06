-- IA-HASH v1.2 schema

CREATE TABLE IF NOT EXISTS prompts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL UNIQUE,
    owner_id TEXT,
    title TEXT NOT NULL,
    description TEXT,
    full_prompt TEXT,
    category TEXT,
    is_master INTEGER DEFAULT 1,
    visibility TEXT DEFAULT 'public',
    h_public TEXT,
    h_secret TEXT,
    signature_prompt TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS iahash_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    iah_id TEXT NOT NULL UNIQUE,
    prompt_id INTEGER,
    type TEXT NOT NULL,
    mode TEXT NOT NULL,
    prompt_hmac_verified INTEGER DEFAULT 0,
    protocol_version TEXT NOT NULL,
    model TEXT,
    timestamp TEXT,
    h_prompt TEXT,
    h_response TEXT,
    h_total TEXT,
    issuer_id TEXT,
    issuer_pk_url TEXT,
    signature TEXT,
    conversation_url TEXT,
    provider TEXT,
    subject_id TEXT,
    store_raw INTEGER DEFAULT 0,
    raw_prompt_text TEXT,
    raw_response_text TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (prompt_id) REFERENCES prompts(id)
);

CREATE TABLE IF NOT EXISTS sequences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    description TEXT,
    category TEXT,
    visibility TEXT DEFAULT 'public',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sequence_steps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sequence_id INTEGER NOT NULL,
    position INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    prompt_id INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY(sequence_id) REFERENCES sequences(id),
    FOREIGN KEY(prompt_id) REFERENCES prompts(id)
);

CREATE INDEX IF NOT EXISTS idx_prompts_category ON prompts(category);
CREATE INDEX IF NOT EXISTS idx_iah_documents_iah_id ON iahash_documents(iah_id);
CREATE INDEX IF NOT EXISTS idx_sequence_steps_sequence_id ON sequence_steps(sequence_id);
