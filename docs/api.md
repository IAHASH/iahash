# IA-HASH API

Base URL: `http://localhost:8000`

## Endpoints

### GET /health
- **Descripción**: Comprobación rápida.
- **Respuesta**: `{ "status": "ok" }`

### POST /issue
- **Descripción**: Emite un documento IA-HASH desde prompt + respuesta.
- **Body JSON**:
  - `prompt_maestro` (str) — requerido
  - `respuesta` (str) — requerido
  - `modelo` (str, opcional)
  - `prompt_id` (str, opcional)
  - `subject_id` (str, opcional)
  - `conversation_id` (str, opcional)
- **Respuesta**: `IAHashDocument` completo con hashes y firma.

### POST /verify
- **Descripción**: Verifica un `IAHashDocument`.
- **Body**: JSON del documento emitido.
- **Respuesta**: `{ "valid": bool, "reason": str }`

### GET /public-key
- **Descripción**: Devuelve la clave pública Ed25519 en PEM.
- **Respuesta**: texto plano PEM.

### GET /master-prompts
- **Descripción**: Listado de prompts maestros aprobados con hash determinista.
- **Respuesta**: lista de objetos `{id, title, version, language, description, prompt_hash}`.

### GET /master-prompts/{prompt_id}
- **Descripción**: Devuelve el prompt maestro completo (incluye `body` y `prompt_hash`).
- **Respuesta**: `{id, title, version, language, category, description, body, prompt_hash, metadata}`.

### POST /master-prompts
- **Descripción**: Crea o actualiza un prompt maestro localmente. Calcula `prompt_hash` si no se envía.
- **Body JSON**: `{id, title, version, language?, category?, description?, body, metadata?, prompt_hash?}`.
- **Respuesta**: prompt maestro persistido con `prompt_hash` calculado.

## Ejemplos

Emitir y verificar con `curl`:

```bash
curl -X POST http://localhost:8000/issue \
  -H "Content-Type: application/json" \
  -d '{
    "prompt_maestro": "Hello",
    "respuesta": "World",
    "modelo": "gpt-demo",
    "prompt_id": "demo-1"
  }' > doc.json

curl -X POST http://localhost:8000/verify \
  -H "Content-Type: application/json" \
  -d @doc.json
```

Obtener clave pública:

```bash
curl http://localhost:8000/public-key
```
