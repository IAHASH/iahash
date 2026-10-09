# IA-HASH — Contrato canónico del producto

Estado: **APROBADO PARA DESARROLLO; REFERENCIA LAB VALIDADA EN PR42–44**. Fecha: 2026-10-10.
El propietario aceptó el contrato indicando que lo único que cambiaría era
la coordinación: al menos tres workers en Torre Cabral y ampliación a seis
o los necesarios si existe capacidad y trabajo independiente. Esa modificación
se incorpora a la campaña; no altera los bytes ni garantías del contrato.
Repositorio: `IAHASH/iahash`. Base auditada: `v1.2`, commit
`96922745e9062b752c163420d4274215f5a6b3ab`. Este documento separa hechos
históricos de reglas propuestas. Aprobar este contrato no equivale a aprobar
un merge, una identidad pública, un despliegue o una política de producción.

## 1. Propósito, alcance y límites

IA-HASH certifica la vinculación ordenada entre dos elementos (PAR1 original,
PAR2 relacionado), sus huellas y, opcionalmente, la recepción por un emisor
externo. Casos: prompt/respuesta, documento/firma, propuesta/aprobación,
acción/resultado, código/revisión, declaración/evidencia, original/traducción.
Las etiquetas describen el uso; no convierten la relación en causalidad.

MVP propuesto: biblioteca Python offline, servidor FastAPI opcional en un
solo nodo con SQLite, cliente Python con cola persistente. Elementos de texto
y bytes; el servidor recibe huellas, no los originales. Ficheros y firmas
de terceros pueden ser elementos binarios, sin interpretar su semántica.

Excluidos: blockchain, Merkle, reputación, marketplace, cuentas públicas,
comparadores, nuevos extractores de proveedores, paneles avanzados, cadenas
de recibos y modificación de Maia. Los adaptadores históricos se conservan
como legado; no entran en el camino de certificación nuevo.

## 2. Garantías y modelo de confianza

| Comprobación | Qué permite afirmar | Qué no demuestra |
| --- | --- | --- |
| Huella con original | Coincidencia de bytes según el perfil declarado | Verdad, titularidad, autoría |
| PAR firmado | El emisor vinculó dos huellas en ese orden | Causalidad ni generación por una IA |
| Recibo externo confiable | El emisor declara haber recibido las huellas y las firmó | Preexistencia pública ni tiempo certificado por un tercero |
| Evidencia de procedencia | Solo lo demostrado por evidencia adicional verificada | No se infiere de una firma o URL |

El servidor de huellas no observa los originales. Su evidencia se denomina
`HASH_RECEIPT`, nunca `SOURCE_OBSERVED`. Un cliente que controla también el
emisor puede autofirmar; la independencia organizativa del testigo se evalúa
fuera de la criptografía. `received_at` es tiempo UTC declarado por el reloj
del emisor, sin garantía de una autoridad de sellado temporal.

El verificador confía en un conjunto local aprobado de
`(issuer_id, environment, key_id, clave pública)`; no confía en una clave
obtenida de un certificado arbitrario. Una firma válida con clave desconocida
se informa como firma válida e identidad no confiable si el llamante aporta
esa clave candidata explícitamente. Sin clave resoluble, `signature` queda
`NOT_CHECKED` y el estado es `KEY_UNAVAILABLE`; no se inventa una firma inválida.
No hay descarga de
URLs ni acceso a red dentro del Core o del verificador nuevo.

## 3. Arquitectura mínima propuesta

| Componente | Responsabilidad | Dependencias permitidas |
| --- | --- | --- |
| Core | Normalización, SHA-256, PAR, firma/validación y vectores | Biblioteca estándar y `cryptography` |
| Server | Entradas, identidad configurada, transacción, recibo y consulta | Core, FastAPI/Pydantic, SQLite |
| Client | Solicitud, cola, reintento, verificación offline y estado | Core, biblioteca HTTP existente |

Core no importa Server, SQLite, HTTP, extractores, prompts maestros o Maia.
La firma pura toma una clave en memoria; leer archivos es una utilidad de
operación separada. Se reutilizan SHA-256 y Ed25519; no se inventan primitivas.
Sin framework de agentes en el runtime, nuevos servicios o base de datos
distribuida. La reorganización de módulos exige analizar importaciones y
preservar adaptadores históricos; no eliminar por antigüedad.

## 4. Hechos históricos congelados (no son vNext)

En la base auditada, `iahash/crypto.py` usa `IAHASH-1.2`:

1. `None` equivale a cadena vacía; NFC de Unicode.
2. CRLF y CR pasan a LF.
3. Cada línea pierde únicamente espacios ASCII y tabuladores finales.
4. Se eliminan líneas vacías finales; se conservan las iniciales e interiores.
5. UTF-8 sin BOM añadido; SHA-256 hexadecimal en minúsculas.

`h_prompt = SHA256(texto normalizado)`; respuesta análoga.
`h_total = SHA256(UTF8(protocol_version + "|" + (prompt_id or "") + "|" +
h_prompt + "|" + h_response + "|" + model + "|" + timestamp))`.
El emisor firma **UTF8 del hexadecimal de h_total**, no sus 32 bytes; la firma
se representa en hexadecimal. `iah_id` es los primeros 16 caracteres del
Base58 Bitcoin de SHA256(UTF8(h_total hexadecimal)). No es el digest completo.

La identidad, URL de clave, tipo, modo, URL de conversación, proveedor,
subject y flags HMAC no están cubiertos por ese agregado. El verificador
histórico no autentica identidad ni recalcula `iah_id`; sin originales puede
devolver flags de contenido positivos. Hay ambigüedad por delimitadores `|`
y divergencia de fallback de `model` entre emisión y verificación. El README
v2 y documentos con `1.2`/base64 no redefinen esos bytes ejecutables.

Históricos `main`, `v1` y `v2` tienen diferencias; `v1` incluye una fórmula
basada en contexto JSON. No se certifica compatibilidad universal por el
número de una rama. Se requiere inventario de fixtures por formato real.

## 5. Versionado y compatibilidad propuestos (D1)

Nuevo identificador de protocolo candidato: `IAHASH-PAIR-1`. La rama `v1.2`
y el nombre comercial no determinan el formato criptográfico. No emitir
certificados nuevos bajo `IAHASH-1.2` con reglas modificadas. Cambio de campos
firmados, normalización, serialización o algoritmos requiere otra versión.

Conservar originales, claves públicas y lectores históricos. No reescribir,
resellar ni atribuir retrospectivamente cobertura a campos no firmados.
Lectura histórica aislada por formato y fixtures; versión desconocida =>
`UNSUPPORTED_VERSION`. Certificados ambiguos => resultado limitado explícito.
No resolver formatos probando algoritmos hasta que alguno devuelva válido.

La emisión histórica existente no se desactiva hasta aprobar su transición.
No se migra masivamente PR #39 ni se fusiona `v2` para obtener el MVP.

## 6. Perfiles de elementos propuestos (D1)

`text-nfc-lf-rstrip-v1`: entrada obligatoria `str`, nunca `None`; aplica los
pasos de texto de §4 y codifica UTF-8. Rechaza sustitutos Unicode aislados.
Permite texto vacío. Un BOM que esté en la entrada se conserva como U+FEFF.
No colapsa espacios interiores ni normaliza mayúsculas. El perfil fija la
base de datos Unicode **15.0.0**, correspondiente a Python 3.12. El runtime
rechaza el perfil si su normalizador no implementa esa versión exacta; añadir
otra versión exige implementación conforme y vectores, no cambiar reglas
según el Python instalado. Dos textos que solo
difieran en espacios finales pueden representar el mismo elemento; se debe
informar al consumidor. Registrar Unicode 15.0.0 en los vectores y comprobar
conformidad en todas las versiones de Python soportadas.

`bytes-v1`: bytes exactos sin transformación, incluyendo el vacío. El Core
acepta bytes; un adaptador lee el fichero. Nunca se interpreta como texto.

En ambos casos `hash = SHA256(bytes resultantes).hexdigest()`, exactamente
64 caracteres `[0-9a-f]`. El perfil forma parte de la huella vinculada. El
servidor valida el formato de las huellas; no afirma haberlas recalculado.

## 7. Serialización canónica y formato PAR propuestos (D1)

`C(obj)` es UTF-8 de JSON con claves ordenadas lexicográficamente, sin
espacios (`separators=(",", ":")`), `ensure_ascii=True`, sin valores NaN.
En los objetos firmados solo se admiten los campos y tipos exactos descritos
aquí: objetos y cadenas ASCII. Sin números, floats, nulls, arrays ni campos
adicionales. Rechazar claves duplicadas y documentos malformados antes de
deserializar en modelos que ignoren campos. No se anuncia compatibilidad JCS.
La normalización del texto ocurre antes de hashear, no sobre el JSON firmado.

Objeto `P` exacto:

```json
{
  "protocol_version": "IAHASH-PAIR-1",
  "par1": {"profile": "text-nfc-lf-rstrip-v1", "hash": "<64 hex>"},
  "par2": {"profile": "bytes-v1", "hash": "<64 hex>"}
}
```

Los marcadores de ejemplos no son valores válidos de certificado.
`pair_bytes = b"IAHASH:PAIR:1\x00" + C(P)`.
`pair_id = SHA256(pair_bytes).hexdigest()` completo, sin truncado.
Cambiar el orden, perfil o huella cambia la entrada del hash. Sin depender
del reloj, modelo, prompt_id o base de datos. No incluye tipos de aplicación.
Nuevos metadatos requieren un esquema versionado; no extensiones no firmadas.

## 8. Certificado y bytes firmados propuestos (D1/D2)

Sobre exacto: `{"body": B, "signature": "<128 hex>"}`.
`B` contiene exclusivamente:

| Campo | Regla |
| --- | --- |
| protocol_version | `IAHASH-PAIR-1` |
| hash_algorithm | `sha256` |
| signature_algorithm | `ed25519` |
| issuer_id | ASCII, regex `[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}` |
| key_id | SHA256 de los 32 bytes de clave pública Ed25519, 64 hex |
| environment | `LAB`, `STAGING` o `PRODUCTION` |
| receipt_id | UUIDv4 canónico en minúsculas, generado por el servidor |
| received_at | UTC `YYYY-MM-DDTHH:MM:SS.ffffffZ`, fecha válida |
| evidence | `HASH_RECEIPT` |
| pair | Objeto `P` exacto de §7 |
| pair_id | Derivado de §7, recalculado al verificar |

`message = b"IAHASH:CERTIFICATE:1\x00" + C(B)`.
`signature = Ed25519.sign(private_key, message).hex()`.
Verificación con la clave pública de `key_id` desde el almacén de confianza,
longitud de firma 64 bytes y chequeo de todos los valores/derivaciones.
Todos los campos del cuerpo están firmados. No hay firma de JSON arbitrario,
hash recursivo, URL de clave autoritativa ni sello encadenado en el MVP.

`receipt_id` identifica una recepción; `pair_id` identifica un PAR. El mismo
PAR puede tener recibos distintos si se solicita una certificación nueva.
Una repetición idempotente devuelve el mismo recibo y los mismos bytes.

## 9. Estados de verificación propuestos

Resultado estructurado con `schema`, `signature`, `issuer_trust`,
`environment`, `pair_binding` y `content` independientes. Valores de chequeo:
`PASS`, `FAIL`, `NOT_CHECKED`; confianza: `TRUSTED`, `UNKNOWN`, `REVOKED`.
Sin originales, `content = NOT_CHECKED`, nunca `PASS`.

Estado resumen: `MALFORMED_CERTIFICATE`, `UNSUPPORTED_VERSION`,
`KEY_UNAVAILABLE`, `INVALID_SIGNATURE`, `UNTRUSTED_ISSUER`, `KEY_REVOKED`,
`ENVIRONMENT_MISMATCH`, `INVALID_PAIR_BINDING`, `CONTENT_MISMATCH`,
`VERIFIED_RECEIPT` o `VERIFIED_CONTENT`. Se devuelve además la lista completa
de fallos, no solo el primero. Para seleccionar un único resumen negativo,
prioridad: MALFORMED_CERTIFICATE, UNSUPPORTED_VERSION, KEY_UNAVAILABLE,
INVALID_SIGNATURE, KEY_REVOKED, UNTRUSTED_ISSUER, ENVIRONMENT_MISMATCH,
INVALID_PAIR_BINDING, CONTENT_MISMATCH. Ningún resumen VERIFIED se selecciona
si existe un fallo. `VERIFIED_RECEIPT` exige esquema, firma,
confianza, entorno y vinculación válidos y ningún original aportado que
falle su comprobación. Un original discrepante siempre produce
`CONTENT_MISMATCH`, nunca `VERIFIED_RECEIPT`. `VERIFIED_CONTENT` exige además
ambos originales presentes y comprobados. Con un único original puede
informarse su chequeo individual sin promover a `VERIFIED_CONTENT`.

Un error de red del cliente es estado de entrega, no firma inválida.
Legado muestra `LEGACY_LIMITED` más formato, cobertura y chequeos efectivos;
no se convierte un `VERIFIED` antiguo en una garantía nueva.

## 10. Identidad y gestión de claves propuestas (D2)

El emisor determina su identidad, entorno y clave desde configuración del
operador. El cliente no puede sustituirlos. Cada entorno tiene directorios,
DB y claves distintos. El verificador requiere el entorno esperado.
Una instalación de laboratorio jamás anuncia identidad oficial por defecto.

Primera inicialización explícita, solo si no existe ninguna clave; privada
ausente con pública presente => fallo cerrado. Pública ausente con privada
válida => derivación sin sustituir privada. Par inconsistente, clave ilegible
o tipo incorrecto => fallo cerrado. Creación exclusiva y permisos privados
desde la apertura, sin sobrescritura ni rotación automática. PEM PKCS8 local
sin cifrado requiere archivo/volumen protegido; no se incluye en la imagen.

Rotación requiere autorización del operador y registro de nueva asociación
de confianza; se conservan públicas antiguas para verificar. Una revocación
impide confianza según política explícita. Sin evidencia temporal adicional,
no afirmar que un recibo precede una clave comprometida basándose solo en su
fecha firmada. Backup de claves privado, separado del registro y cifrado
por el procedimiento operativo; prueba de recuperación en LAB.

## 11. API nueva propuesta (D1/D2)

Namespace `/api/pair-v1` para no reinterpretar rutas históricas.

| Método/ruta | Entrada | Resultado |
| --- | --- | --- |
| POST `/receipts` | Objeto P + `Idempotency-Key` | 201 certificado confirmado; repetición 200 mismo certificado |
| GET `/receipts/{receipt_id}` | UUIDv4 | 200 certificado original; 404 desconocido |
| POST `/verify` | Sobre + originales opcionales codificados según perfiles | Resultado de §9, sin red |
| GET `/issuer` | Ninguna | Identidad/entorno/key_id/PEM público; informativo, no raíz de confianza |
| GET `/health` | Ninguna | Liveness mínimo, sin datos privados |
| GET `/ready` | Ninguna | DB y clave utilizables; 503 si no |

Formato exacto de POST `/verify`: objeto con `certificate` (sobre de §8)
y `originals` opcional. `originals` es un objeto con `par1` y/o `par2`.
Para perfil de texto: `{"text":"..."}`; para bytes: `{"base64":"..."}`.
Un campo por elemento, sin campos adicionales, nulls ni ambos formatos;
debe coincidir con el perfil firmado. Omisión de elemento implica
NOT_CHECKED. Los originales no entran en el cuerpo firmado; se contrastan
con las huellas. La codificación base64 inválida produce 422, y un original
bien formado con huella diferente produce CONTENT_MISMATCH.

Idempotency-Key: 32 bytes aleatorios, 64 hex minúsculas, persistida antes del
envío. Se almacena con `(issuer_id, environment)` y digest canónico de P.
Misma clave y P => mismo certificado; distinta P => 409, sin sobrescritura.
Comparar semántica canónica, no orden o whitespace del JSON recibido.

JSON estricto, Content-Type requerido, límites previos a lectura/parseo.
Propuesta LAB: 16 KiB para emisión; 3 MiB para verificar, originales hasta
1 MiB cada uno (bytes en base64 RFC4648 estándar con padding; texto en JSON).
No se guardan originales de `/verify` ni se registran en logs. Ninguna ruta
nueva recibe URLs para recuperar contenido o claves. Error estable:
`{"error":{"code":"...","message":"..."}}`, sin trazas ni secretos.
400 JSON inválido; 401/403 acceso; 409 idempotencia; 413 tamaño; 422 esquema;
429 límite; 503 indisponibilidad. Resultado criptográfico negativo bien
formado devuelve 200 con chequeos fallidos, nunca excepción genérica.

Acceso de emisión, consulta y verificación restringido al operador/cliente
autorizado; política inicial propuesta: token compartido LAB en cabecera,
comparación segura, TLS para conexiones entre máquinas. No construir cuentas
públicas. Límites configurables iniciales: 60 peticiones/minuto por token,
4 escrituras concurrentes, `Retry-After` en 429; no se presentan como capacidad
medida. Autenticación y límites operativos se revisan antes de STAGING.

## 12. Persistencia, privacidad y conservación propuestas (D3)

SQLite en un solo nodo; archivo persistente configurado en un volumen,
`foreign_keys=ON`, `busy_timeout=5000`, WAL y `synchronous=FULL` propuestos.
Contener recibo canónico, firma, identidad/entorno/key_id, clave idempotente
y digest de petición. UNIQUE para receipt_id y clave idempotente por emisor
y entorno. Una transacción hace la comprobación idempotente y persistencia;
solo devolver confirmado después del commit. Fallo tras commit y antes de
respuesta => el reintento recupera ese mismo recibo. Colisión inesperada de
UUID => regenerar antes de insertar, sin sobrescribir evidencia.

Ni originales ni prompt/HMAC/identidades de sujeto por defecto. Las huellas
de contenido predecible pueden permitir ataques de diccionario: hashes no
equivalen a anonimización. No servir registros privados por rutas públicas.
No incorporar la idempotency-key en el certificado exportable.

Propuesta: sin purga automática de metadatos en LAB; conservación definitiva,
retención de backups e intercambio con producción requieren decisión D3.
No eliminar historia existente ni inferir autorización de borrado.
Schema version explícita; migraciones revisadas con copia previa, transacción
donde SQLite lo permita y fallo cerrado. Nunca borrar DB ante errores.
`rollback()` sin transacción DDL explícita no garantiza deshacer cada ALTER.

Backup SQLite mediante API de backup/snapshot consistente, no copiar solo
`.db` ignorando WAL vivo. Restaurar en directorio separado, comprobar
`integrity_check`, conteo/recibos/firmas y correspondencia de clave antes de
cambiar el volumen. Conservar original hasta validar. Readiness fallida no
autoriza reinicialización, cambio de clave ni borrado.

## 13. Cliente y contrato de integración

Estados de entrega: `PENDING`, `SENDING`, `CONFIRMED`, `REJECTED`.
Persistir P, idempotency-key, emisor/entorno esperado e intentos antes de
enviar. Reinicio con `SENDING` => volver a `PENDING` con la misma clave.
`CONFIRMED` solo tras verificar firma, confianza, entorno y pair_id de la
respuesta frente a la solicitud y persistir el certificado localmente.

Timeouts propuestos: conexión 3 s, lectura 10 s. Reintentar cortes de red,
408, 429 y 5xx; máximo 5 intentos por ejecución, backoff exponencial
(esperas 1, 2, 4 y 8 s entre cinco intentos, con jitter y respetando
Retry-After). Agotar intentos deja
PENDING para reanudación explícita. Otros 4xx => REJECTED; certificado
incorrecto => REJECTED con evidencia diagnóstica, nunca confirmado.
Sin redirecciones que envíen credenciales a otro origen. Nunca generar una
clave idempotente nueva por un timeout. La simulación de Maia usa esta misma
interfaz; no modifica Maia ni requiere sus dependencias.

## 14. Seguridad y operación

Antes de exposición: resolver SSRF de las rutas históricas, confianza de
emisores, autenticación, límites de entrada, acceso al registro y CORS.
No basta con asegurar únicamente el namespace nuevo si permanecen rutas
históricas inseguras expuestas. Desactivar adaptadores en perfil de servicio
mínimo solo como cambio documentado y revisado, manteniendo lectores offline.

Docker reproducible con dependencias fijadas tras validar, usuario sin
privilegios, volúmenes de registro/claves explícitos, sin claves de prueba
embebidas, health/readiness y comprobación de restauración. Compatibilidad
base: Python 3.12; ampliar versiones solo con CI y vectores. Logs mínimos
sin contenidos, tokens o privadas. Rollback de código mantiene DB y claves;
si schema nuevo impide volver atrás, restauración desde copia validada,
sin sobrescribir operaciones posteriores. No desplegar públicamente.

## 15. Aceptación y gates

Cada requisito necesita prueba positiva y negativa reproducible:

| Área | Evidencia exigida |
| --- | --- |
| Core offline | Importar/emitir/verificar sin DB, servidor, internet ni Maia |
| Normalización | Unicode compuesto/descompuesto, CRLF/CR/LF, tabs, vacíos, BOM, sustitutos rechazados |
| Hash/PAR | Vectores públicos deterministas, orden/perfil, delimitadores sin ambigüedad |
| Firmas | Vector Ed25519 fijo, clave incorrecta, manipular cada campo firmado y firma |
| Confianza | Clave arbitraria no oficial, revocación, emisor/entorno incorrectos |
| DB | Reinicio, esquema desconocido/corrupto, error de migración sin pérdida, copia/restauración |
| Claves | Ausencia de cada archivo, recuperación de pública, mismatch, permisos y creación exclusiva |
| Idempotencia | Solicitudes repetidas/concurrentes, mismo key distinto P, commit con respuesta perdida |
| Cliente | Timeout/red, reintento limitado, cola tras reinicio, respuesta falsa, pendientes no confirmados |
| API | Validación estricta, límites, auth, no SSRF, consulta y no filtrar originales |
| Historia | Fixtures por formato real, lectura sin alterar bytes ni atribuir garantías nuevas |
| Operación | Docker LAB, persistencia, restore y rollback documentados y ensayados |

**Gate G1:** D1/D2/D3 y este contrato aprobados antes de cambios de protocolo.
G1 satisfecho por la respuesta del propietario de 2026-10-10, con la única
modificación de concurrencia descrita al comienzo. No autoriza merge ni
despliegues públicos. Los apartados titulados «propuestos» describen la
especificación ahora aprobada para implementar, no funcionalidad terminada.
Mientras tanto: auditorías, vectores históricos, regresiones y correcciones
compatibles de preservación en PR #41. No declarar el MVP terminado por una
PR creada ni por una suite parcial verde. Registrar por separado implementado,
probado, revisado, fusionado y desplegado.

## 16. Decisiones adoptadas y límites pendientes

Consultar `IAHASH_DECISIONS.md` para alternativas A/B/C y recomendación.
D1 aprobada: garantías/formato nuevo, perfiles y política de lectura histórica.
D2 aprobada para LAB: identidad y confianza por entorno, inicialización y acceso.
D3 aprobada para LAB: conservación mínima y copias, sin purga ni borrado histórico.
Identidades operativas, rotación/retención de producción y exposición pública
siguen pendientes de decisiones separadas. Implementación/evidencia de esta
referencia: `IAHASH_CAMPAIGN.md`; no confundir aprobación con despliegue.
Licencia Apache-2.0 existente se conserva; costes e infraestructura pública
no se modifican. Cualquier cambio posterior en ellos requiere autorización.
