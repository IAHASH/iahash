# IA-HASH — Decisiones para aprobar el contrato

Estado: propuestas pendientes. Fecha: 2026-10-10. Responsable de aprobación:
propietario humano del proyecto. Aprobar requiere respuesta explícita; el
silencio no aprueba. Referencia: `IAHASH_PRODUCT_CONTRACT.md`.

## D1 — Formato, garantías y compatibilidad criptográfica

| Alternativa | Ventajas | Inconvenientes |
| --- | --- | --- |
| A. Mantener emisión v1.2 como única versión | Mínimo cambio, lectores actuales | Delimitadores ambiguos, campos de identidad sin cobertura, semántica ligada a IA |
| B. Añadir `IAHASH-PAIR-1`, perfiles texto/bytes, PAR canónico y cuerpo completo firmado; lectores históricos aislados | PAR independiente, cobertura explícita, sin reinterpretar firmas antiguas, verificación offline | Nuevo esquema y vectores; adaptación de consumidores; política de transición |
| C. Reescribir v1.2 con nuevas reglas o fusionar v2 como sustitución | Una etiqueta aparente | Rompe significado criptográfico, historia ambigua; PR39 es principalmente documental |

**Recomendación: B**, con las reglas exactas de §§5–9 del contrato.
Lectura histórica limitada por fixtures reales, sin borrar ni reemitir
certificados previos. Emisión vieja continúa hasta decidir su transición.
El servidor nuevo certifica recepción de huellas (`HASH_RECEIPT`), sin afirmar
procedencia ni autoridad temporal independiente. Texto normalizado conserva
reglas observadas; binario conserva bytes exactos.

Decisión solicitada: aprobar B y la cobertura/perfiles propuestos, o señalar
qué garantía/formato debe cambiar antes de implementar. No se solicita
autorización para fusionar PR ni para modificar certificados históricos.

## D2 — Identidad, claves y confianza por entorno

| Alternativa | Ventajas | Inconvenientes |
| --- | --- | --- |
| A. Confiar en cualquier clave indicada por el documento | Autohospedaje sin configuración | No acredita identidad; exposición a SSRF; puede aparentar emisor oficial |
| B. LAB con identidad explícita del operador, claves distintas por entorno, trust store local fijado y token LAB | Simple, offline, separa firma de identidad y laboratorio de producción | Alta/rotación/revocación requieren gestión explícita; confianza no automática |
| C. PKI pública o autoridad temporal externa desde el MVP | Puede aportar servicios de identidad/tiempo adicionales | Costes, infraestructura, dependencias y alcance prematuros |

**Recomendación: B**. No asignar aún identidad oficial ni tocar claves reales.
La inicialización es explícita; pérdida de privada falla; pública recuperable
desde privada. Conservar públicas históricas. Revocación no implica prueba
de cuándo fue emitido un recibo. Rotación requiere autorización operativa.
Token LAB para emisión/consulta/verificación; no cuentas públicas.

Decisión solicitada: aprobar este modelo LAB. El identificador y las claves
reales del emisor se provisionarán después, mediante el operador, cuando
exista autorización de operación; no son necesarios para pruebas efímeras.
STAGING/PRODUCTION y su infraestructura siguen fuera de autorización.

## D3 — Conservación, privacidad y recuperación

| Alternativa | Ventajas | Inconvenientes |
| --- | --- | --- |
| A. Guardar originales y purgar automáticamente según TTL nuevo | Facilita algunas verificaciones | Exposición de contenido privado y posible pérdida irreversible; política no acordada |
| B. Solo huellas/recibos/idempotencia, sin purga automática en LAB; backups consistentes y restauración explícita | Evidencia mínima, reintentos recuperables, preserva historia | Huellas no anónimas; crecimiento del registro; retención definitiva pendiente |
| C. Sin persistencia o registro temporal en memoria | Menos estado | No resiste reinicios ni respuesta perdida; no satisface MVP |

**Recomendación: B**. No borrar historia existente ni hacer migración
destructiva. El contrato limita el almacenamiento nuevo; no autoriza eliminar
raw histórico. No se fija retención de producción ni de backups sin decisión
posterior. El ensayo LAB usará datos sintéticos y copias aisladas.

Decisión solicitada: aprobar conservación mínima sin purga LAB. Si se desea
TTL, definir antes el período, alcance de datos/copias y efectos sobre
idempotencia y consulta; nunca inferirlo de un fallo de inicialización.

## Decisiones técnicas resueltas como propuesta sin bloquear auditorías

Python 3.12, SHA-256/Ed25519 existentes, FastAPI monolítico modular, SQLite
un nodo, cliente Python y cola local. Sin Merkle, blockchain o cadena de
recibos. Límites y backoff iniciales documentados y configurables; medir
antes de escalado. Conservar licencia Apache-2.0. Ningún gasto, despliegue,
DNS, modificación de Maia o fusión automática.

## Registro de aprobación

| Decisión | Estado | Evidencia |
| --- | --- | --- |
| D1 | PENDIENTE | Ninguna aprobación recibida |
| D2 | PENDIENTE | Ninguna aprobación recibida |
| D3 | PENDIENTE | Ninguna aprobación recibida |

Gate G1 permanece cerrado. Auditorías y correcciones compatibles de
preservación pueden avanzar mediante PR revisables mientras se decide.
