# IA-HASH: Documento Maestro del Proyecto (v1.2)

## 🧭 Resumen Ejecutivo

IA-HASH es un protocolo abierto y sistema software diseñado para verificar la **autenticidad, integridad y contexto** de contenidos generados por modelos de lenguaje (LLMs). Permite firmar outputs de IA de forma verificable, usando criptografía moderna y estructuras estandarizadas.

Se puede integrar fácilmente en cualquier pipeline de generación o consulta, y su objetivo final es **crear un estándar universal de confianza** para los contenidos generados por IA.

## 🧩 Filosofía y Motivación

* **Confianza en entornos post-generativos:** IA-HASH permite demostrar que una IA específica generó cierto contenido, bajo cierto contexto, y que este no ha sido modificado.
* **Modelo agnóstico:** Compatible con cualquier IA, proveedor o sistema.
* **Abierto, verificable y simple:** Todo está basado en estructuras públicas y sin dependencias propietarias.
* **Fácil de usar:** Ideal tanto para aplicaciones web como para CLI o integraciones con LLMOps.

## 📜 Especificación del Protocolo (v1.2)

### Formato del Documento IA-HASH (simplificado):

```json
{
  "protocol_version": "IAHASH-1.2",
  "iah_id": "...",
  "timestamp": "...",
  "prompt_id": "...",
  "type": "PAIR | CONVERSATION",
  "mode": "LOCAL | TRUSTED_URL",
  "h_prompt": "...",
  "h_response": "...",
  "h_total": "...",
  "model": "gpt-4",
  "issuer_id": "iahash.local",
  "issuer_pk_url": "http://localhost:8000/keys/issuer_ed25519.pub",
  "signature": "...",
  "prompt_hmac_verified": true,
  "subject_id": "...",
  "conversation_url": "...",
  "provider": "OpenAI",
  "store_raw": false,
  "raw_prompt_text": null,
  "raw_response_text": null
}
```

* Hashes SHA256 normalizados (`h_prompt`, `h_response`, `h_total`).
* Firma Ed25519 de `h_total` y metadatos con la clave privada local.
* Verificación offline o vía endpoint `/api/check`.
* `prompt_hmac_verified` indica que el documento referencia un `prompt_id` registrado; el HMAC real se delega a la tabla `prompts`.
* `store_raw` determina si los textos planos se conservan en base de datos; por defecto son `null` para proteger privacidad.

## 🏗️ Arquitectura del Sistema

```
[User] → [Web UI (Jinja)] → [FastAPI Backend]
                        ↘
           [Extractores (ChatGPT share)]
                          ↓
                 [issuer.py / verifier.py]
                          ↓
               [SQLite (db/schema.sql)]
                          ↓
                [JSON firmado + clave pública]
```

* Backend: `FastAPI` (API + vistas HTML), firmado en tiempo real vía `issuer.py`.
* Frontend: plantillas Jinja y estáticos en `web/templates` y `web/static`.
* Base de datos: SQLite (`db/schema.sql`, auto-init en startup) gestionada por `iahash/db.py`.
* Claves: Ed25519 en `/data/keys/issuer_ed25519.private|pub`, generadas por `start.sh` si no existen.
* Stateless: el documento firmado es autosuficiente; la BD solo almacena histórico y prompts.

## 🔁 Flujo de Emisión

1. Usuario genera texto con IA
2. App llama a `/api/verify/pair` o `/api/verify/conversation`
3. Se calculan hashes de entrada y salida
4. Se construye documento IA-HASH completo
5. Se firma y se almacena (opcional)
6. Se devuelve JSON verificable

## ✅ Flujo de Verificación

1. Cliente recibe documento `.json`
2. Llama a `/api/check` con el contenido
3. Servidor valida:

   * Hashes
   * Firma
   * Clave pública
   * Prompt HMAC (si aplica)
4. Devuelve resultado `ok | invalid | tampered`

## 🌐 API (Endpoints)

```http
GET    /                → Web (index)
GET    /api             → Info general
GET    /health          → Healthcheck
POST   /api/verify/pair → Genera IA-HASH (prompt + respuesta local)
POST   /api/verify/conversation → Genera IA-HASH desde URL de conversación (ChatGPT share)
POST   /api/check       → Verifica un documento IA-HASH existente
GET    /verify          → UI de emisión/verificación manual
GET    /compare         → UI de comparación
GET    /prompts         → Lista de prompts (HTML)
GET    /prompts/{slug}  → Detalle de prompt (HTML)
GET    /sequences       → Lista de secuencias (HTML)
GET    /sequences/{slug}→ Detalle de secuencia (HTML)
GET    /iah/{id}        → Consulta un documento emitido (HTML)
GET    /public-key      → Clave pública en JSON
GET    /keys/issuer_ed25519.pub → Clave pública PEM
```

## 🗃️ Base de Datos

Esquema SQLite (`schema.sql`) contiene:

* `prompts`: prompts base con HMAC opcional y slug público.
* `iahash_documents`: documentos emitidos (JSON completo; `raw_*` solo si `store_raw=1`).
* `sequences` y `sequence_steps`: flujos guiados y sus pasos.

La inicialización es automática en arranque (`ensure_db_initialized`), apuntando por defecto a `db/iahash.db`.

## 🔐 Seguridad: Claves, Hashes, Firmas

* Firmas Ed25519 con clave privada generada en arranque (`/data/keys/issuer_ed25519.private`).
* Verificación con clave pública (`/data/keys/issuer_ed25519.pub` o `/public-key`).
* SHA256 para todos los textos
* Documentos firmados incluyen metainformación del firmante

## 🖥️ Web: Funcionalidad, UI y Roadmap

Frontend muy simple:

* `index.html` → bienvenida e info
* `verify.html` → emisión/validación manual
* `compare.html` → comparación de IA-HASH
* `prompts.html`, `prompt_detail.html`, `sequences.html`, `sequence_detail.html`, `docs.html` → navegación de contenidos
* `styles.css` → estilo
* `logo.png` → marca

Próximas mejoras:

* Visualizador y verificador desde navegador
* Upload de JSON y validación visual

## 🧠 Glosario

* **IAH Document**: JSON verificable que representa un output IA firmado
* **HMAC Prompt**: Verificación extra del prompt base
* **Issuer**: Entidad que firma (modelo, organización, etc.)
* **Hash**: SHA256 de entrada/salida
* **Raw text**: Prompt/response/contexto en texto plano

## ✅ Checklist de Conformidad IA-HASH

* [x] Usa protocolo v1.2 o superior
* [x] Incluye `iah_id`, hashes, modelo, timestamp
* [x] Incluye firma Ed25519
* [x] Incluye URL de clave pública
* [x] Incluye contexto opcional (prompt, conversación, sujeto)

## 🚧 Roadmap Futuro

* [ ] Firma externa por terceros
* [ ] Modo "verificación federada"
* [ ] Backends alternativos (PostgreSQL, Redis)
* [ ] Plugins para LLMs y notebooks
* [ ] Portal público de verificación

## 📎 Apéndices

### A. Clave Pública (JSON)

```json
{
  "issuer_pk_url": "/keys/issuer_ed25519.pub",
  "pem": "-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----"
}
```

### B. IA-HASH de ejemplo

```json
{
  "iah_id": "IAH:20251205:XYZ123",
  "protocol_version": "IAHASH-1.2",
  "type": "PAIR",
  "mode": "LOCAL",
  "model": "gpt-4.1",
  "h_prompt": "...",
  "h_response": "...",
  "h_total": "...",
  "issuer_id": "IAHASH:001",
  "signature": "base64...",
  ...
}
```

### C. Manual de verificación rápida

1. Borrar cualquier base de datos previa: `rm -f db/iahash.db`.
2. Levantar el servidor (`uvicorn api.main:app --reload` o el stack Docker).
3. Abrir `/prompts` y confirmar que aparece **CV Honesto Cognitivo**.
4. Ir a `Verificar > Prompt+URL`, seleccionar el prompt `cv` y pegar una URL `chatgpt.com/share/...` de prueba.
5. Copiar el JSON IA-HASH generado y pegarlo en el tab **Checker**.
6. Verificar que el resultado es válido y que no aparece el error “Missing issuer_pk_url and issuer_id does not match local issuer”.

---

> Última revisión: 2025-12-07 — Basado en versión `v1.2`, alineado con archivos `PROTOCOL_1.2.md`, `ARCHITECTURE_1.2.md`, `db.py`, `main.py`, `issuer.py`, `ROADMAP.md` y estructura real del sistema.
