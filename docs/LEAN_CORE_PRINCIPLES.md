# IA-HASH — Principios del núcleo ligero

**Objetivo:** una librería pequeña que calcula y verifica huellas y firmas; un servicio opcional que emite recibos persistentes. No construir un framework.

## Mantener
- Pares arbitrarios como primitiva. Prompt/respuesta es un adaptador, no una dependencia del núcleo.
- SHA-256 + Ed25519 ya implementados, salvo fallo demostrado; preservar lectura de certificados históricos.
- Una única canonicalización versionada y vectores de prueba.
- API mínima: emitir, verificar, consultar recibo, clave pública, health.
- Datos mínimos: huellas, firma, identidad de clave, instante de recepción, versión, estado y enlace previo opcional.
- Cliente con reintento e idempotencia; sin dependencia de Maia en el servidor.

## Evitar por ahora
- Blockchain, Merkle, SDK múltiples, dashboards, cuentas, prompts maestros, extractores LLM y secuencias en el camino crítico.
- Dependencias adicionales sin necesidad demostrable.
- Migración a PostgreSQL por moda: SQLite puede ser suficiente en un solo nodo con WAL, backups y pruebas de restauración; medir antes.
- Hacer que el hash pruebe autoría o causalidad: el certificado solo prueba lo observado y firmado por su emisor.

## Regla para cada PR
1. Un problema concreto y reproducible.
2. Cambio mínimo compatible.
3. Test negativo y positivo.
4. Impacto en tamaño, dependencias y superficie de ataque.
5. Ningún despliegue, merge o cambio en Maia sin autorización.

## Próximo gate
Revisar CI y ejecutar tests; añadir pruebas aisladas para arranque con clave privada existente, pública ausente, par inconsistente y primera inicialización no autorizada.
