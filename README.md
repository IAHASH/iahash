# IA-HASH v1.2

IA-HASH es un sistema de sellado y verificación para contenido generado por IA. v1.2 incorpora API FastAPI, frontend mínimo, base de datos SQLite auto-inicializada, firmas Ed25519 y extractor de conversaciones compartidas de ChatGPT.

## Estructura
```
iahash/
  api/main.py             # API + páginas HTML
  iahash/                 # Núcleo criptográfico y DB
  web/templates/          # Jinja2 templates
  web/static/             # CSS y assets
  db/schema.sql           # Tablas SQLite
  db/seed_prompts.sql     # Datos iniciales
  start.sh                # Inicializa claves, DB y arranca Uvicorn
```

## Arranque rápido
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
./start.sh
# UI en http://localhost:8000
```
`start.sh` crea claves Ed25519 en `/data/keys` y, si falta, inicializa `db/iahash.db` con el esquema oficial.

## Endpoints principales
- `POST /api/verify/pair` — genera IA-HASH para par de textos.
- `POST /api/verify/conversation` — lee URL compartida de ChatGPT y emite IA-HASH.
- `POST /api/check` — verifica un documento IA-HASH.
- `GET /api/iah/{iah_id}` — consulta pública de IA-HASH.
- `GET /api/prompts` y `GET /api/prompts/{slug}` — prompts maestros.
- `GET /api/sequences` y `GET /api/sequences/{slug}` — secuencias y pasos.
- `GET /keys/issuer_ed25519.pub` — clave pública del emisor.

La web incluye páginas `/prompts`, `/verify`, `/compare`, `/sequences` y `/iah/{iah_id}`.

## Protocolo
La normalización sigue PROTOCOL_1.2.md:
- Unicode NFC
- CRLF → `\n`
- Trim de espacios finales y líneas en blanco al final
- Hash SHA256 en hex
- Firma Ed25519 sobre `h_total`

`iah_id = base58(SHA256(h_total))[0:16]`.

## Base de datos
Tablas: `prompts`, `iahash_documents`, `sequences`, `sequence_steps`. Los textos raw solo se almacenan si `store_raw = 1`.

## Mejoras rumbo a v1.2
Sugerencias concretas para cerrar la versión se documentan en `docs/V1.2_IMPROVEMENTS.md`.

## Licencia
Apache-2.0.
