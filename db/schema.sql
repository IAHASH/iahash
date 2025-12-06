-- db/schema.sql
-- Qué/por qué: Definir tabla de prompts para IA-HASH (categorías, versiones, etc.)

CREATE TABLE IF NOT EXISTS prompts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL UNIQUE,          -- 'cv', 'debilidades', etc.
    code TEXT NOT NULL,                 -- 'CV_HONESTO_V1'
    category TEXT NOT NULL,             -- 'profesional', 'autoconocimiento', ...
    title TEXT NOT NULL,                -- 'CV Honesto Cognitivo'
    short_description TEXT NOT NULL,    -- 'Retrato profesional sincero'
    body TEXT NOT NULL,                 -- prompt completo
    version TEXT NOT NULL,              -- 'v1'
    enabled INTEGER NOT NULL DEFAULT 1, -- 1 = activo
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_prompts_slug
    ON prompts(slug);

CREATE INDEX IF NOT EXISTS idx_prompts_category
    ON prompts(category);
