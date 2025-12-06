IA-HASH – Arquitectura v1.2

Esta arquitectura describe el funcionamiento completo de IA-HASH v1.2, incluyendo su web, API, backend, base de datos y extensiones.

1. Estructura del repositorio
iahash/
  api/
    main.py

  iahash/
    crypto.py
    issuer.py
    verifier.py
    db.py
    models.py
    extractors/
      chatgpt_share.py

  web/
    templates/
      base.html
      index.html
      prompts.html
      prompt_detail.html
      sequences.html
      sequence_detail.html
      verify.html
      compare.html
      docs.html
      account.html
    static/
      styles.css
      logo.png

  db/
    schema.sql
    seed_prompts.sql

  docs/
    PROTOCOL_1.2.md
    ARCHITECTURE_1.2.md
    VISION.md
    ROADMAP.md

  start.sh
  Dockerfile
  requirements.txt
  README.md

2. Backend – FastAPI

El backend expone los endpoints IA-HASH.

Principales:
PAIR Verification
POST /api/verify/pair

Conversation Verification (ChatGPT URL)
POST /api/verify/conversation

Checker
POST /api/check

Consultar IA-HASH por ID
GET /api/iah/{iah_id}

Prompts
GET /api/prompts
GET /api/prompts/{slug}

3. Frontend (HTML minimalista estilo Flarum)

Menú:

Home

Prompts

Sequences

Compare

Verify

Docs

Account

Páginas clave:

/prompts/{slug}

Muestra el prompt maestro

Botón “Copiar prompt”

Campo para pegar URL de ChatGPT

Botón “Generate IA-HASH”

Historial de ejecuciones

Botón “Convert to Sequence”

Bloque de secuencia (si aplica)

/verify

Tres pestañas:

Pair (text A + text B)

Prompt + URL (ChatGPT)

Checker (pegas IA-HASH JSON)

/compare

Dos modos:

Consistencia (mismo modelo)

Coherencia (distintos modelos)

No guardamos contenido → se re-lee desde URL bajo demanda.

4. Base de datos – SQLite (auto-init)
prompts

Define prompts maestros y privados.

iahash_documents

Almacena verificados:

hashes

metadatos

modelo

timestamp

URL

NO contenido (salvo store_raw = 1)

sequences, sequence_steps

Soporte de secuencias tipo:

Dejar de fumar

Hábitos

Aprendizaje

Rutinas IA

5. Sistema de claves

En /start.sh:

Si no existen claves, generar par Ed25519.

Guardarlas en /data/keys/ (persistente).

Claves por ahora:

issuer_ed25519.private

issuer_ed25519.pub

6. Extractor de ChatGPT

Archivo:

iahash/extractors/chatgpt_share.py


Responsable de:

descargar chat remoto,

extraer prompt original,

extraer respuesta final,

obtener nombre de modelo,

devolver error claro si falla.

7. Sistema de secuencias

Una secuencia es un “prompt padre” con steps:

Día 0

Día 1

Semana 1

Mes 1

Las secuencias viven en:

/sequences

/sequences/{slug}

Los steps pueden ser:

prompts maestros

prompts derivados

prompts privados

8. IA-HASH ID (público)

Cada verificación genera un ID corto:

iah_id = base58(SHA256(h_total))[0:16]


La URL pública:

/iah/{iah_id}


muestra:

metadatos,

hashes,

firma,

proveedor,

estado,

NO texto.

9. Extensibilidad

Módulos de extractor por proveedor:

chatgpt_share

claude_share

gemini_share

API estable desde raíz /api.

Web server lista para añadir:

login ligero

“cuaderno de prompts”

panel de usuario

exportaciones
