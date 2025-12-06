# Integración y ejemplos

## Python

```python
from iahash.issuer import issue_document
from iahash.verifier import verify_document

prompt = "Analiza este texto"
respuesta = "La IA responde con..."

Doc = issue_document(prompt_text=prompt, respuesta_text=respuesta, modelo="gpt-5")
valid, reason = verify_document(Doc)
```

## Node/JS

```bash
curl -X POST http://localhost:8000/issue \
  -H "Content-Type: application/json" \
  -d '{"prompt_maestro":"Hola","respuesta":"Mundo","modelo":"gpt"}'
```

## SQL (idea)

Guarda `prompt_id`, `subject_id`, `conversation_id`, `h_total`, `firma_total` y la URL `chatgpt.com/share/...` en tu tabla `prompts`. Con eso puedes mapear el hash a tu usuario y al enlace compartido para trazabilidad completa.
