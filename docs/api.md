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
- **Descripción**: Placeholder de prompts maestros aprobados.
- **Respuesta**: lista de objetos `{id, title, language, description, prompt}`.

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
