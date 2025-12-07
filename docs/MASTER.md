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
  "iah_id": "...",
  "timestamp": "...",
  "prompt_id": "...",
  "type": "pair|conversation",
  "h_prompt": "...",
  "h_response": "...",
  "h_total": "...",
  "model": "gpt-4",
  "protocol_version": "1.2",
  "issuer_id": "IAHASH:001",
  "issuer_pk_url": "/keys/issuer_ed25519.pub",
  "signature": "...",
  "prompt_hmac_verified": true,
  "subject_id": "...",
  "conversation_url": "...",
  "provider": "OpenAI",
  "store_raw": true,
  "raw_prompt_text": "...",
  "raw_response_text": "...",
  "raw_context_text": "..."
}
```

* Hashes SHA256 normalizados.
* Firma Ed25519 de `h_total` y metadatos.
* Verificación offline o via endpoint `/api/check`.

## 🏗️ Arquitectura del Sistema

```
[User] → [Web UI] → [FastAPI Backend] → [SQLite + Claves] → [Signed JSON]
                                 ↓
                           [API pública REST]
```

* Backend: `FastAPI`, firmado en tiempo real vía `issuer.py`
* Frontend: HTML/CSS simple (`web/`)
* Base de datos: SQLite (`db/`)
* Claves: Ed25519, en `/data/keys/`
* Stateless: Todo el documento es autosuficiente y portable

## 🔁 Flujo de Emisión

1. Usuario genera texto con IA
2. App llama a `/api/verify/pair` o `/verify/conversation`
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
GET    /api            → Info general
GET    /health         → Healthcheck
POST   /api/verify/pair → Genera documento (pair)
POST   /api/verify/conversation → Genera documento (URL)
POST   /api/check      → Verifica documento
GET    /prompts        → Lista de prompts
GET    /sequences      → Lista de secuencias
GET    /iah/{id}       → Consulta un documento
GET    /public-key     → Clave pública en JSON
GET    /keys/issuer_ed25519.pub → Clave pública PEM
```

## 🗃️ Base de Datos

Esquema SQLite (`schema.sql`) contiene:

* `prompts`: prompts base con HMAC opcional
* `iahash_documents`: documentos emitidos (campos JSON completos)
* `sequences`: flujos guiados de verificación

Todos los accesos se hacen vía `db.py` con columnas tolerantes a versiones.

## 🔐 Seguridad: Claves, Hashes, Firmas

* Firmas Ed25519 con clave privada generada en arranque (`/data/keys/issuer_ed25519.key`)
* Verificación con clave pública (`issuer_ed25519.pub`)
* SHA256 para todos los textos
* Documentos firmados incluyen metainformación del firmante

## 🖥️ Web: Funcionalidad, UI y Roadmap

Frontend muy simple:

* `index.html` → bienvenida e info
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
  "type": "pair",
  "model": "gpt-4",
  "h_prompt": "...",
  "h_response": "...",
  "h_total": "...",
  "issuer_id": "IAHASH:001",
  "signature": "base64...",
  ...
}
```

---

> Última revisión: 2025-12-07 — Basado en versión `v1.2`, alineado con archivos `PROTOCOL_1.2.md`, `ARCHITECTURE_1.2.md`, `db.py`, `main.py`, `issuer.py`, `ROADMAP.md` y estructura real del sistema.
