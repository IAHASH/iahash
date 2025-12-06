<p align="center">
  <img src="https://raw.githubusercontent.com/IAHASH/iahash/main/web/logo.png" width="120" />
</p>

<h1 align="center">IA-HASH</h1>

<p align="center">Prompt + Respuesta → Hash + Firma Ed25519 → Verificación offline.</p>

---

## 📌 Arquitectura actual

- **Librería**: `iahash/` (crypto, modelos Pydantic, emisión y verificación).
- **API**: `api/main.py` con FastAPI (`/issue`, `/verify`, `/public-key`, `/health`, `/master-prompts`).
- **Frontend**: `web/` (HTML + CSS + JS vanilla) usando la API.
- **Scripts**: generación de claves y demo CLI en `scripts/`.
- **Tests**: `pytest` en `tests/`.
- **Docker**: imagen ligera lista para ejecutar `start.sh`.

## 🔄 Flujo "issue → verify" (texto)

1. Normaliza prompt y respuesta (`\r\n` → `\n`, trim finales, UTF-8).
2. Calcula `h_prompt = SHA256(normalise(prompt))` y `h_respuesta = SHA256(normalise(respuesta))`.
3. Calcula `h_total = SHA256(version | prompt_id | h_prompt | h_respuesta | modelo | timestamp)`.
4. Firma `h_total` con la clave privada Ed25519 (`firma_total`).
5. Empaqueta todo en un `IAHashDocument` (JSON) con metadatos, hashes y firma.
6. Para verificar: recalcula hashes, recomputa `h_total` y valida la firma con la clave pública.

## 📄 Esquema JSON de IAHashDocument (resumen)

```json
{
  "version": "IAHASH-1",
  "prompt_id": "CV_v01",
  "prompt_maestro": "...texto exacto...",
  "respuesta": "...respuesta IA...",
  "modelo": "gpt-5.1",
  "timestamp": "2025-01-01T15:32:11Z",
  "subject_id": "user-123",
  "conversation_id": null,
  "h_prompt": "<64 hex>",
  "h_respuesta": "<64 hex>",
  "h_total": "<64 hex>",
  "firma_total": "<hex>",
  "issuer_id": "iahash.com",
  "issuer_pk_url": "https://.../public-key.pem"
}
```

## 🔑 Claves: generación y uso

- Las claves viven en `keys/` (se ignoran en Git). Puedes reubicarlo con `IAHASH_KEYS_DIR`.
- Genera par Ed25519 con `scripts/generate_keys.py` (se ejecuta automáticamente desde `start.sh` si faltan).
- La API sirve la clave pública en `/public-key` (PEM) para verificaciones externas.

## 🚀 Instalación local

```bash
git clone https://github.com/IAHASH/iahash
cd iahash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Genera claves y arranca API + web UI:

```bash
./start.sh
# API en http://localhost:8000, UI en http://localhost:8000/
```

## 🛠️ Uso desde CLI (demo)

```bash
python scripts/demo_issue_verify.py
```

Imprime un IA-HASH JSON, luego lo verifica localmente usando la misma clave pública.

## 🌐 Uso de la API (cURL)

Emitir:

```bash
curl -X POST http://localhost:8000/issue \
  -H "Content-Type: application/json" \
  -d '{
    "prompt_maestro": "Hello IA",
    "respuesta": "This is the answer",
    "modelo": "gpt-demo",
    "prompt_id": "demo-1",
    "subject_id": "user-42"
  }'
```

Verificar:

```bash
curl -X POST http://localhost:8000/verify \
  -H "Content-Type: application/json" \
  -d @documento.json
```

Obtener clave pública:

```bash
curl http://localhost:8000/public-key
```

## 🐍 Uso desde Python

```python
from iahash.issuer import issue_document
from iahash.verifier import verify_document

doc = issue_document(
    prompt_text="Hello",
    respuesta_text="World",
    modelo="gpt-demo",
    prompt_id="demo-1",
    subject_id="user-42",
)

valid, reason = verify_document(doc)
print(valid, reason)
```

## 📜 Diseño y principios

- **Neutral**: funciona con cualquier modelo (cloud u on-premise).
- **Sin blockchain**: sólo SHA256 + Ed25519 + JSON.
- **Offline-first**: la verificación funciona años después, sin servidores externos.
- **Reproducible**: normalización estricta garantiza hashes estables.
- **Extensible**: campos opcionales como `conversation_id` para conversaciones completas.

## 📚 Documentación adicional

- Protocolo detallado: [`docs/protocol.md`](docs/protocol.md)
- API: [`docs/api.md`](docs/api.md)
- Integración y ejemplos: [`docs/integration-examples.md`](docs/integration-examples.md)

## 🤝 Contribuir

1. Haz fork y crea rama.
2. Añade tests (`pytest`).
3. Envía PR descriptivo.

Licencia: Apache-2.0.
