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
    -- Hash público del prompt maestro (para verificar que no ha cambiado)
    h_public TEXT,
    -- HMAC interno del prompt maestro (NO se expone)
    h_secret TEXT,
    signature_prompt TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS iahash_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Identificador único IA-HASH (IAH-ID)
    iah_id TEXT NOT NULL UNIQUE,

    -- Relación opcional con un prompt maestro
    prompt_id INTEGER,

    -- Tipo de documento IA-HASH: PAIR | CONVERSATION
    type TEXT NOT NULL,

    -- Modo de verificación: LOCAL | TRUSTED_URL
    mode TEXT NOT NULL,

    -- Si el prompt maestro fue verificado vía HMAC (true/false)
    prompt_hmac_verified INTEGER DEFAULT 0,

    -- Versión del protocolo IA-HASH (ej: IAHASH-1.2)
    protocol_version TEXT NOT NULL,

    -- Modelo utilizado (ej: gpt-5.1-thinking)
    model TEXT,

    -- Timestamp ISO8601 del sellado
    timestamp TEXT,

    -- Hashes individuales y total
    h_prompt TEXT,
    h_response TEXT,
    h_total TEXT,

    -- Datos del emisor / firma
    issuer_id TEXT,
    issuer_pk_url TEXT,
    signature TEXT,

    -- Origen de la conversación (ChatGPT, Claude, etc.)
    conversation_url TEXT,
    provider TEXT,

    -- Identificador del sujeto/autora del contenido (opcional)
    subject_id TEXT,

    -- Flags de almacenamiento de contenido crudo
    store_raw INTEGER DEFAULT 0,

    -- Texto crudo del prompt, respuesta y contexto (si se decide almacenar)
    raw_prompt_text TEXT,
    raw_response_text TEXT,
    raw_context_text TEXT,

    -- Copia del documento IA-HASH completo (JSON serializado)
    -- Sirve para re-descargar, re-verificar o mostrar el .iahash original.
    json_document TEXT,

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

-- Índices útiles

CREATE INDEX IF NOT EXISTS idx_prompts_category
    ON prompts(category);

CREATE INDEX IF NOT EXISTS idx_iah_documents_iah_id
    ON iahash_documents(iah_id);

CREATE INDEX IF NOT EXISTS idx_iah_documents_prompt_id
    ON iahash_documents(prompt_id);

CREATE INDEX IF NOT EXISTS idx_sequence_steps_sequence_id
    ON sequence_steps(sequence_id);
