# IA-HASH Protocol

## Normalización de texto

- Convertir `\r\n` y `\r` a `\n`.
- Eliminar espacios finales de cada línea.
- Codificar en UTF-8.
- Función de referencia: `iahash.crypto.normalise`.

## Hashes

- `h_prompt = SHA256(normalise(prompt_maestro))`
- `h_respuesta = SHA256(normalise(respuesta))`
- `h_total = SHA256(version | prompt_id | h_prompt | h_respuesta | modelo | timestamp)`
  - El separador es `"|"`.
  - `prompt_id` vacío (`""`) cuando es `None`.

## Firma

- Algoritmo: **Ed25519**.
- Se firma la cadena hex `h_total` en UTF-8.
- Firma en hexadecimal: `firma_total`.
- Clave pública servida en `/public-key` (PEM). Puede verificarse con libs estándar (OpenSSL, libsodium, cryptography).

## Esquema JSON IAHashDocument

Campos principales (ver `iahash.models.IAHashDocument`):

- `version`: protocolo ("IAHASH-1").
- `prompt_id` (opcional): identificador lógico de la plantilla.
- `prompt_maestro`: texto exacto enviado a la IA.
- `respuesta`: respuesta completa devuelta por la IA.
- `modelo`: nombre del modelo (gpt-*, claude-*, local, etc.).
- `timestamp`: ISO8601 en UTC (sufijo `Z`).
- `subject_id` (opcional): usuario/sujeto asociado.
- `conversation_id` (opcional): reservado para conversaciones completas.
- `h_prompt`, `h_respuesta`, `h_total`: hashes SHA256 en hex.
- `firma_total`: firma Ed25519 en hex.
- `issuer_id`, `issuer_pk_url`: metadatos del emisor.

## Flujo de emisión

1. Normalizar textos.
2. Calcular `h_prompt` y `h_respuesta`.
3. Construir cadena y `h_total`.
4. Firmar `h_total` con la clave privada.
5. Publicar documento y clave pública.

## Flujo de verificación

1. Normalizar textos recibidos y recalcular `h_prompt` y `h_respuesta`.
2. Recalcular `h_total` con los metadatos recibidos.
3. Comparar `h_total` local vs `h_total` del documento.
4. Verificar `firma_total` con la clave pública Ed25519.
5. Resultado booleano + motivo textual.

## Integración recomendada

- Guarda `prompt_id`, `subject_id`, `conversation_id` y la URL compartida del chat (si existe) en tu SQL para trazabilidad.
- Versiona las claves: rota el par Ed25519 según tus políticas y publica la clave pública histórica para verificaciones futuras.
- Para validar enlaces `chatgpt.com/share/...`, recupera el prompt/respuesta, aplica la misma normalización y compara con `h_prompt`/`h_respuesta`.
