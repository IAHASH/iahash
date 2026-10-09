# IA-HASH — Estado de campaña

Actualizado: 2026-10-10 (Europe/Madrid). Coordinador: chat actual IA-HASH.
Campaña existente continuada en PR40/41. Sin campaña/PR duplicada.

## Objetivo y base

Objetivo actual: cerrar reconocimiento y preparar contrato canónico
revisable; reforzar preservación compatible mientras se decide el protocolo.
Base: `v1.2@96922745e9062b752c163420d4274215f5a6b3ab`.
Contrato: `docs/IAHASH_PRODUCT_CONTRACT.md`, **propuesta no aprobada**.
Decisiones: `docs/IAHASH_DECISIONS.md`, D1/D2/D3 pendientes.
**G1 cerrado:** no implementar ni emitir el protocolo propuesto hasta aprobación.

## Trabajo y propiedad

| Propietario | Tarea | Estado | Reserva de archivos |
| --- | --- | --- | --- |
| Coordinador | Contrato, ADR, auditoría consolidada, estado y PR | Entrega para revisión humana | Ninguna reserva activa |
| Worker Core/Architect | Bytes históricos, cobertura, vectores y revisión del contrato | Completado; vectores locales PASS | Liberada |
| Worker Architect | API/DB/operación, historia main/v1/v2/PR39 | Auditoría estática completada | Liberada |
| Worker Server/QA | Preservación, claves, overrides, carreras y regresión | 25 pruebas locales y CI PASS | Liberada |

Workers activos al cerrar esta entrega: **0**. Máximo observado: 3 simultáneos.
No workers o automatizaciones residentes. No archivos compartidos editados
simultáneamente; coordinador publicó únicamente tras liberar reservas.
La siguiente sesión debe leer este archivo y las PR antes de crear tareas.

## PR y estados separados

| PR | Rama / commit de referencia | Implementado | Probado | Revisado | Fusionado | Desplegado |
| --- | --- | --- | --- | --- | --- | --- |
| [40](https://github.com/IAHASH/iahash/pull/40) | audit/independent-sealing-baseline-20261009; base documental anterior 60569a16b42b16a5e2f7ba682f6aa8f61d7862f3 | Contrato/ADR/auditoría/estado y vectores, sin protocolo nuevo | Vector histórico local PASS; CI de esta entrega pendiente al publicarla | Revisión técnica del contrato; aprobación humana pendiente | No | No |
| [41](https://github.com/IAHASH/iahash/pull/41) | fix/preserve-db-and-issuer-keys@06f01372b2c1ced21f46f85de7ca7530d507bfb5 | Preservación SQLite y claves + regresión | 25 locales; 25 en Ubuntu + shell PASS | Worker QA y coordinador; revisión humana pendiente | No | No |
| [39](https://github.com/IAHASH/iahash/pull/39) | v2@117e035571d3df864957161780a42281289673ac | Transición histórica principalmente documental | No ejecutada en esta campaña | Inspección estática; conflictos observados | No | No |

PR terminadas/fusionadas por esta campaña: ninguna. Ambas entregas 40/41
permanecen como borradores. No declarar un MVP por esta entrega documental.
El commit propio de este archivo se obtiene del head actual de PR40; no se
inserta una referencia circular a su hash dentro del mismo commit.

## Evidencia de pruebas

Baseline oficial: colección abortada en test_chatgpt_share_parsing por
`_collect_messages` ausente; tres módulos saltados. Ejecución del resto:
**26 passed, 9 failed, 3 skipped** en Windows/Python3.12. Detalle y versiones:
`docs/IAHASH_BASELINE_AUDIT.md`. No confundir con regresiones introducidas.

PR41 exacta: 25 pruebas locales PASS (9.07 s en revisión coordinador).
[CI Ubuntu](https://github.com/IAHASH/iahash/actions/runs/37999377119/job/114053441814)
en `06f01372`: **25 passed (4.36 s)**, permisos POSIX y sintaxis shell
superados. Migra preservando evidencia, sin garantía de DDL atómico.
Backup/restore probado con SQLite sintético, sin sistema de copias productivo.

Vectores históricos: `python tools/verify_legacy_vectors.py`, PASS local;
normalización, firma del hex, manipulaciones, clave incorrecta y ambigüedad
`|`. JSON público: `docs/vectors/legacy-v1.2.json`, semilla pública de prueba.
La CI de PR40 debe confirmar esos mismos bytes, sin implementar formato nuevo.

## Bloqueos y riesgos abiertos

- Aprobación humana D1 (nuevo formato/compatibilidad), D2 (identidad/confianza
  LAB), D3 (retención mínima sin purga LAB). El mandato adjunto exige este gate.
- SSRF y confianza en emisor, auth/límites/privacidad de rutas históricas.
- Colección y nueve fallos históricos; inventario de certificados reales
  todavía insuficiente para prometer compatibilidad total.
- Migraciones DDL pueden quedar parcialmente aplicadas; no borrar ni
  reintentar con reinicialización automática. Claves antiguas deben conservarse.
- Core aislado, servidor idempotente, cliente durable, Docker/restore y
  simulación Maia aún no implementados como MVP nuevo ni aprobados para operación.

## Cola siguiente, sin tareas duplicadas

| Orden | Tarea concreta | Propietario | Depende de |
| --- | --- | --- | --- |
| 1 | Revisar/decidir D1–D3 sobre contrato exacto | Humano + Coordinador | Entrega PR40 |
| 2 | Revisar preservación/CI y decidir merge de PR41 | Humano + QA | No depende de cambio de protocolo |
| 3 | Congelar fixtures por formatos históricos e investigar parser/tests divergentes | Worker Core/QA | Puede continuar sin G1; PR separada pequeña |
| 4 | Tests simulados SSRF/trust/privacidad y corrección compatible acordada | Worker Server/QA | No requiere producción; revisar cambios de acceso |
| 5 | Core offline conforme y vectores nuevos | Worker Core | G1 aprobado |
| 6 | Transacción/idempotencia/recuperación Server | Worker Server | Core y contrato aprobados |
| 7 | Cliente Python durable + simulador Maia | Worker Client/QA | API aprobada, sin tocar Maia |
| 8 | Docker LAB, backups/restore/rollback y validación completa | Worker Server/QA | MVP probado; autorización de operación separada |

Sin autorización de producción, DNS, costes, secretos operativos, Maia ni
merge automático. Revertir documentación retirando los archivos de propuesta;
revertir código conserva registros y claves y no recupera garantías perdidas
por volver a código destructivo. No hay despliegue que revertir aquí.
