IA-HASH – Protocolo v1.2 (Oficial)

IA-HASH v1.2 es un estándar abierto para verificar la autenticidad e integridad de salidas generadas por modelos de IA.
Su objetivo principal es asegurar que una respuesta proviene realmente de una IA, dada un prompt específico, sin manipulaciones posteriores.

Se centra en dos modos:

PAIR → Sellado de dos piezas de texto (texto A + texto B).

CONVERSATION → Verificación de PROMPT + RESPUESTA obtenidas desde una URL compartida de ChatGPT u otros proveedores.

1. Objetivos del protocolo

Garantizar integridad

Garantizar autenticidad

Garantizar relación causal PROMPT → RESPUESTA

Permitir verificación offline sin servidores

Evitar almacenamiento innecesario de contenido sensible

Ser implementable por cualquier herramienta en pocas horas

2. Normalización (Regla Fundamental)

Antes de calcular cualquier hash, ambos textos—prompt y respuesta—deben ser normalizados:

Unicode limpio

Reemplazar CRLF → \n

Eliminar espacios en blanco al final de cada línea

Eliminar líneas en blanco finales sobrantes

Convertir a UTF-8 bytes

Salida: bytes_normalizados

La normalización garantiza que:

mismo contenido → mismos hashes

3. Hashes del Protocolo IA-HASH

Se calculan siempre como SHA256 en hexadecimal.

3.1 Hash de prompt
h_prompt = SHA256(normalised_prompt)

3.2 Hash de respuesta
h_response = SHA256(normalised_response)

3.3 Hash combinado
cadena_total = protocol_version | prompt_id | h_prompt | h_response | model | timestamp
h_total      = SHA256(cadena_total)


Donde:

protocol_version = "IAHASH-1.2"

prompt_id = identificador único del prompt maestro (o null para prompts libres)

model = modelo usado (ej: gpt-5.1)

timestamp = ISO8601

4. Firma criptográfica (Ed25519)
signature = Ed25519_sign(private_key, h_total)


Quien verifique necesitará solo:

El IA-HASH JSON

La clave pública (issuer_pk_url)

5. Documento IA-HASH v1.2

Es un objeto JSON estándar, con estos campos:

{
  "protocol_version": "IAHASH-1.2",

  "type": "PAIR | CONVERSATION",
  "mode": "LOCAL | TRUSTED_URL",

  "prompt_id": "cv_honest_v1",
  "prompt_hmac_verified": true,

  "timestamp": "2025-12-07T17:54:00Z",
  "model": "gpt-5.1",

  "h_prompt": "<sha256>",
  "h_response": "<sha256>",
  "h_total": "<sha256>",

  "signature": "<ed25519_signature>",
  "issuer_id": "iahash.com",
  "issuer_pk_url": "https://iahash.com/keys/issuer_ed25519.pub",

  "conversation_url": "https://chatgpt.com/share/xxxx",
  "provider": "chatgpt",

  "subject_id": null,
  "store_raw": false,
  "raw_prompt_text": null,
  "raw_response_text": null,

  "iah_id": "ABCD1234EFGH5678"
}

6. Tipos de verificación
A) PAIR

Sellado de texto manual.

Uso:

Cuando el usuario pega contenido propio.

Cuando no existe URL verificable.

B) CONVERSATION

Verificación completa PROMPT + RESPUESTA desde URL compartida.

Pasos:

Descargar contenido original desde ChatGPT.

Extraer:

prompt

respuesta

Normalizar ambos.

Verificar si prompt == prompt_maestro.

Generar hashes.

Firmar.

Es el core del proyecto.

7. Identificador único IA-HASH (IAH-ID)

Cada documento IA-HASH genera un ID único:

iah_id = base58(SHA256(h_total))[0:16]


Permite URLs como:

https://iahash.com/iah/7x9KabcDeF23LmNp

8. Clave pública del prompt maestro

Para cada prompt maestro:

Normalizar texto

Calcular:

h_public = SHA256(prompt_norm)
h_secret = HMAC(K_iahash, prompt_norm)   # NO expuesto


Publicar:

h_public

firma del prompt (opcional)

información del prompt

De esta forma, si el prompt cambia, la verificación falla.

9. Verificación externa / Checker

Cualquier tercero puede verificar un documento IA-HASH usando:

El JSON

La clave pública

(Opcional) los textos originales o la URL

Salida:

VALID
INVALID_SIGNATURE
HASH_MISMATCH
PROMPT_MISMATCH
UNREACHABLE_SOURCE
UNSUPPORTED_PROVIDER

10. Extensibilidad

El protocolo está diseñado para:

Claude shared links

Gemini shared links (cuando sean públicos)

PDFs

Otros modelos LLM

Secuencias verificables

Comparadores de consistencia y coherencia

IA-HASH v1.2 define las bases para todo ello.
