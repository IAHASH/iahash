# IA-HASH — Reconocimiento y evidencia reproducible

Fecha: 2026-10-10, Europe/Madrid. Continúa PR #40/#41, sin campaña paralela.
Base oficial auditada: `v1.2@96922745e9062b752c163420d4274215f5a6b3ab`.
Se revisó código real, pruebas, dependencias, historia y PR abiertas.
No se accedió a producción, claves reales, Maia, DNS o infraestructura pública.

## Referencias comprobadas

| Rama | Commit observado | Evaluación |
| --- | --- | --- |
| v1.2 (predeterminada) | 96922745e9062b752c163420d4274215f5a6b3ab | Base de reconocimiento, API ejecutable v1.2 |
| main | b2ac43b19effdf58d6598aa034985016223012e3 | Rutas/esquema de otra generación |
| v1 | 61a836fc64347b3b995769d769dd612c49184766 | Verificador con contexto JSON; no asumir fórmula README |
| v2 | 117e035571d3df864957161780a42281289673ac | API aún declara 1.2; nombre no acredita Core nuevo |
| codex/fix-chatgpt-share-conversation-parser | f2839cfdc02d267266ad7fc3ce7befd750fcf5ad | Rama histórica de parser, no integrada ni validada aquí |
| audit/independent-sealing-baseline-20261009 | 60569a16b42b16a5e2f7ba682f6aa8f61d7862f3 antes de esta entrega | PR40, documentación inicial reutilizada |
| fix/preserve-db-and-issuer-keys | 3359b1c9dcc2b0c6770dfa8e9b1bf7b3b1e8bfe6 antes de esta entrega | PR41, corregida y ampliada en 06f01372b2c1ced21f46f85de7ca7530d507bfb5 |

[PR39](https://github.com/IAHASH/iahash/pull/39): abierta, conflicto de merge
observado, `v2 -> v1.2`, 13 commits y seis archivos principalmente de docs y
ejemplos. No implementa por sí misma el núcleo genérico descrito por README.
[PR40](https://github.com/IAHASH/iahash/pull/40) y
[PR41](https://github.com/IAHASH/iahash/pull/41): abiertas, borradores, no
fusionadas. No se crearon PR ni campañas duplicadas.

## Arquitectura real y reutilización

`start.sh` inicia `uvicorn api.main:app`. FastAPI mezcla frontend, catálogos,
secuencias, extracción remota, emisión y checker. `issuer.py` siempre persiste
en SQLite; `store_raw=False` evita originales pero no evita el registro.
`verifier.py` importa issuer y extractores y descarga claves/conversaciones.
`iahash/__init__.py` importa esos módulos: aún no existe Core offline aislado.
`api/main.py` inicializa DB durante importación y startup; DB está en el árbol
del código (`iahash/db.py:17`). Docker no prueba persistencia por sí mismo.

Reutilizar normalización/SHA-256/Ed25519, primitivas existentes, FastAPI,
SQLite, fixtures y partes de Docker. Cliente durable/idempotencia, emisor
externo con confianza configurada y Core independiente siguen pendientes.

## Hallazgos que condicionan el desarrollo

| Prioridad | Evidencia en la base | Consecuencia/acción |
| --- | --- | --- |
| Crítica | `iahash/db.py:60–78` intenta borrar SQLite ante esquema incompleto o error | PR41 conserva archivo y registros; revisar antes de merge |
| Alta | `start.sh` regeneraba las dos claves cuando faltaba la pública | PR41 recupera pública, falla sin privada y crea exclusivamente |
| Alta | `verifier.py:43–89` obtiene URL de clave del documento; `api/main.py:584–597` descarga HttpUrl con redirects | SSRF/trust pendientes; pruebas con transporte simulado, no sondas de red |
| Alta | `crypto.py:161–165`, `issuer.py:294–306` cubren solo seis campos indirectos | Identidad/tipo/modo/URL/subject/flags/ID no firmados; D1 requiere nuevo formato |
| Alta | Sin auth/cuotas observadas; `api/main.py:794–817` devuelve documentos y raw almacenados | Acceso al registro y privacidad deben resolverse antes de exposición |
| Media | `issuer.py:273–306`, `db.py:473–480`: timestamp en segundos, ID determinista, INSERT simple | Repetición puede colisionar; no es idempotencia durable |
| Media | `verifier.py:245,291` inicializa flags positivos sin originales/secreto | Distinguir NOT_CHECKED de comprobación superada |
| Media | DDL incremental sin transacción explícita | Preservar registros no garantiza rollback de todas las columnas |
| Media | Requisitos sin versiones, pytest en runtime, Docker sin usuario explícito | Fijar dependencias y ensayar Docker/restore después de aprobar contrato |

Otras duplicaciones: composición de h_total en crypto/issuer con fallback de
modelo distinto; reglas de claves en paths/crypto/start; modelos en API y
models; extracción en API y extractor. `router.py` importa módulos ausentes y
no es el router usado. Doble `/static`; `/docs` personalizado colisiona con
Swagger. Analizar importaciones/uso antes de retirar archivos históricos.

README anuncia v2 estable, `iahash/core` y rutas/variables que no existen en
la base. `docs/protocol.md`, MASTER y PROTOCOL_1.2 contienen nombres, versiones,
encoding de firma y garantías divergentes. La especificación propuesta
documenta los bytes ejecutados en vez de redefinir historia por esos textos.

## Pruebas ejecutadas y sus límites

Entorno local: Windows, Python 3.12, Unicode 15.0.0. Copias independientes de
commits públicos, sin DB/claves de operación. Los tests de API generan DB
en la copia local; no se ejecutan contra `sources/` ni despliegues. Se recuperó
también el logo binario original y se verificó su blob Git
`f01fead0a9f9f8d9f188dee163a0ac763c843462` para no atribuir su ausencia a código.

1. `python -m pytest -q` en baseline: colección interrumpida por ImportError
   `_collect_messages` de `tests/test_chatgpt_share_parsing.py`; tres módulos
   históricos saltados. No equivale a suite completa ejecutada.
2. `python -m pytest -q --ignore=tests/test_chatgpt_share_parsing.py` en baseline:
   **26 passed, 9 failed, 3 skipped**. Nueve fallos: expectativa destructiva
   de test_db_init (además sensible al archivo abierto en Windows), dos
   fixtures/parser issue-from-share, un texto de error del verifier, tres
   verify_conversation y dos verify_share con mocks incompatibles con timeout.
   No se modificaron esos adaptadores para ocultar el resultado.
3. PR41 ampliada: `python -m pytest -q tests/test_db_init.py
   tests/test_registry_preservation.py tests/test_key_preservation.py`:
   **25 passed**. Conservación ante corruptos/vacíos/esquema/migración/seed,
   reinicios, backup/restauración explícita y claves parciales/mismatch,
   overrides, permisos de creación y escritores concurrentes. No valida el
   resto del producto ni asegura atomicidad de migraciones históricas.
4. `python tools/verify_legacy_vectors.py`: **PASS** con crypto.py real
   cargado sin paquete/DB/red. Vectores públicos en `docs/vectors/legacy-v1.2.json`:
   Unicode/LF/vacíos, hashes/ID, firma Ed25519 del hexadecimal UTF-8,
   firma/mensaje alterados, clave incorrecta y digest binario rechazados.
   Reproduce misma firma bajo dos distribuciones de model/timestamp con `|`.
   Semilla pública RFC8032 de pruebas, nunca identidad operativa.
   [CI Ubuntu de vectores](https://github.com/IAHASH/iahash/actions/runs/37999715192/job/114054541559)
   superada en `1953213e650ceae52db0d13fab6ed9ef946827a0`.

Dependencias directas observadas en ejecución: FastAPI 0.143.0, Starlette
1.7.0, cryptography 50.0.2, Pydantic 2.14.0, pytest 9.1.1, httpx 0.28.1,
beautifulsoup4 4.15.0, Jinja2 3.1.6, uvicorn 0.54.0. Requisitos históricos
sin fijar hacen que otra fecha de instalación pueda producir otros resultados.
No es una auditoría de vulnerabilidades de estas versiones.

CI previa PR41 (`3359b1c`): job `114033875137`, success, solo dos regresiones
y `sh -n`. CI nueva ejecuta las tres suites/25 casos y shell en Ubuntu.
Consultar el commit exacto de PR41 y el estado de campaña para el resultado
remoto; no trasladar una CI verde de otro commit. CI en
`06f01372b2c1ced21f46f85de7ca7530d507bfb5`: job
[`114053441814`](https://github.com/IAHASH/iahash/actions/runs/37999377119/job/114053441814)
**success**, logs: 25 passed en 4.36 s y `sh -n start.sh` superado. POSIX y
shell se validaron en ese job Ubuntu, no localmente en Windows.

## Próximas acciones y revisión

1. Aprobar o ajustar D1/D2/D3 del contrato propuesto; cambios de protocolo
   bloqueados por G1. No hace falta decidir producción para pruebas LAB.
2. Revisar PR41 y CI nueva. Sin merge automático; mantener DB/claves al revertir.
3. QA: fixtures/versiones históricas, SSRF simulado, confianza de emisor y
   privacidad del registro; reparar suite por tareas pequeñas independientes.
4. Tras G1: consolidar Core offline, servidor transaccional/idempotente y
   cliente con pendientes; luego simulación Maia y Docker LAB/restore.

No se han verificado proveedores remotos actuales, explotación SSRF,
compatibilidad de todos los certificados históricos, rendimiento, Docker,
volúmenes reales ni un servicio desplegado. No afirmar MVP completado.
