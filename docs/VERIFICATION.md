# IA-HASH — Verificación end-to-end de Prompt + Respuesta

Este documento resume el flujo recomendado para asegurar que un prompt y su respuesta corresponden exactamente a lo que se registró en tu base de datos y, cuando aplique, a la conversación compartida (por ejemplo `https://chatgpt.com/share/...`).

## 1. Emisión (issuer)
1. Normaliza `prompt_maestro` y `respuesta` (CRLF→LF, trimming, UTF-8).
2. Calcula `h_prompt` y `h_respuesta` con SHA-256 en hexadecimal.
3. Construye `h_total = SHA256(version | prompt_id | h_prompt | h_respuesta | modelo | timestamp)`.
4. Firma `h_total` con Ed25519 (`firma_total`).
5. Guarda en SQL los campos de trazabilidad: `prompt_id`, `subject_id`, `conversation_id` y, opcionalmente, `share_url` del chat.
6. Devuelve el JSON IA-HASH al cliente.

## 2. Almacenamiento en SQL
- Tabla recomendada: `prompts` (ver `db/schema.sql`).
- Relaciona cada `prompt_id` y `subject_id` con `conversation_id` o `share_url` para auditoría futura.
- No almacenes claves privadas en la base de datos; sólo la metadata necesaria para enlazar la verificación.

## 3. Verificación
1. Recibe el documento IA-HASH.
2. Normaliza y re-hashea `prompt_maestro` y `respuesta`; compara con `h_prompt` y `h_respuesta`.
3. Recalcula `h_total` con los metadatos y comprueba que coincide.
4. Verifica la firma Ed25519 usando la clave pública servida por `/api/public-key`.
5. (Opcional) Si se proporciona `conversation_id` o `share_url`, recupera el contenido del chat (ChatGPT share) y confirma que el prompt/respuesta coinciden con el registro de SQL y con el documento.

## 4. ¿Qué garantiza?
- Integridad: cualquier modificación en prompt, respuesta o metadatos rompe los hashes.
- Autenticidad: la firma asegura que el documento proviene del emisor legítimo.
- Trazabilidad: el enlace con tu SQL y el `conversation_id` permite auditar frente a la conversación original.

## 5. Limitaciones actuales
- La extracción automática desde enlaces `chatgpt.com/share/...` está prevista como módulo futuro; hoy el verificador espera que el prompt y la respuesta sean iguales a los almacenados y a los presentes en el JSON.
- La clave privada debe mantenerse fuera del repositorio y montarse en tiempo de despliegue.

## 6. Próximos pasos sugeridos
- Implementar un servicio que lea el share link de ChatGPT y lo normalice para verificación automática.
- Añadir endpoints para consultar historial por `conversation_id` y validar múltiples turnos.
- Sincronizar los prompts maestros (`db/promts.sql`) con la UI de “Master Prompts” para emisión guiada.
