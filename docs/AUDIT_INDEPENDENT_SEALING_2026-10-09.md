# IA-HASH — Auditoría inicial del sellado independiente (2026-10-09)

Estado: **auditoría estática parcial; no se han ejecutado pruebas ni desplegado servicios**.

## Fuente de verdad y alcance
- Repositorio: `IAHASH/iahash`; rama predeterminada comprobada: `v1.2`.
- Archivos inspeccionados: `README.md`, `api/main.py`, `iahash/issuer.py`, `iahash/verifier.py`, `iahash/crypto.py`, `iahash/db.py`, `requirements.txt`, `Dockerfile`, `start.sh`.
- El README describe v2.0 / Universal Pairs, pero el backend y el arranque aún declaran v1.2; **no asumir implementación v2.0 completa**. Resolver versiones sin invalidar certificados antiguos.

## Componentes reutilizables
- FastAPI, rutas existentes y frontend.
- SHA-256, normalización y firmas Ed25519 existentes.
- Emisor de pares y verificador con resolución de claves públicas.
- SQLite y esquema histórico; Docker y script de arranque.
- Extractores y prompts históricos: preservar sin ampliar alcance del MVP.

## Riesgos y brechas observadas (revisar y reproducir antes de corregir)
1. `api/main.py` monta `/static` dos veces y configura CORS abierto con `allow_credentials=True`; revisar comportamiento y política antes de exponer el servicio.
2. `iahash/db.py::ensure_db_initialized` contiene rutas que eliminan el archivo de base de datos al detectar esquema incompleto o una excepción. **Riesgo crítico de pérdida de registros**. Prohibir migraciones destructivas; exigir respaldo, prueba de recuperación y migración explícita.
3. `start.sh` genera un par nuevo si falta cualquiera de los dos archivos de clave. Si falta solo la pública, puede reemplazar la privada existente y romper verificaciones históricas. Implementar recuperación de pública desde privada; si falta privada, fallo cerrado salvo inicialización explícita.
4. `iahash/crypto.py` escribe la clave privada en PEM sin cifrar. Auditar permisos de archivos, volumen, identidad del proceso y separación de claves por entorno.
5. `iahash/verifier.py` obtiene `issuer_pk_url` de documentos y realiza solicitudes HTTP; evaluar SSRF, allowlist/trust store, redirecciones, límites y confianza en identidad del emisor.
6. `iahash/issuer.py` firma pares y persiste documentos, pero el código revisado no demuestra por sí solo un testigo externo con recibo persistente, idempotencia y cadena auditada.
7. `iahash/issuer.py` acepta `issuer_id` y `issuer_pk_url` proporcionados por cliente. Asegurar que identidad y clave anunciada correspondan a la clave que realmente firma.
8. No se han verificado autenticación, rate limits, copias de seguridad, tests completos ni despliegue actual. No afirmar que existen o funcionan.

## Modelo de confianza obligatorio
- **PAIR_LOCAL / client-asserted**: demuestra integridad del par presentado al emisor, no procedencia acreditada del LLM.
- **SOURCE_OBSERVED**: el servidor ha recuperado evidencia de una fuente; registrar alcance, método y limitaciones.
- **EXTERNALLY_SEALED**: el servicio externo confirma recepción de huella con fecha de servidor y firma verificable; no garantiza verdad ni autenticidad original.
- Nunca mostrar un simple `VALID` como prueba de que un modelo concreto produjo la respuesta sin evidencia adicional.

## Plan de implementación en PR pequeñas
1. **Gate de seguridad**: tests de regresión para DB no destructiva, claves, SSRF y confianza del emisor; corregir sin romper certificados previos.
2. **Contrato vNext**: definir canonicalización y bytes firmados, versión y esquema, `key_id`, `environment`, `receipt_id`, `received_at`, `content_hash`, `previous_receipt_hash` opcional, y estados de verificación. Versionar; no reescribir v1.2.
3. **Registro persistente**: idempotencia, transacciones, comprobantes firmados, consultas y pruebas de alteración; no guardar contenido original por defecto.
4. **Resiliencia**: reintentos con backoff, cola local y estado `PENDING_EXTERNAL_SEAL`; nunca etiquetar pendientes como certificados.
5. **Cliente Maia**: contrato y simulador independientes; coordinar con Maia 00 antes de tocar su repositorio.
6. **Operación**: Docker reproducible, health/readiness, permisos, backup/restore, rotación de claves, staging y rollback. Clouding/DNS solo tras autorización expresa.

## Criterios de aceptación del MVP
- Emisión y verificación reproducibles de par1/par2 y certificado externo.
- Verificación independiente de la firma con clave pública **confiable**.
- Manipular cualquier elemento firmado invalida el resultado.
- Distinguir laboratorio y producción criptográfica y visualmente.
- Reinicio, caída de red y reintento idempotente no producen pérdida ni duplicación indebida.
- Una migración o ausencia de clave jamás borra evidencia histórica ni rota claves silenciosamente.
- Suite automática y recuperación desde copia probada antes de producción.

## Límites de autorización
No modificar Maia, Torre Cabral, Clouding, DNS, secretos, facturación ni producción. No fusionar PR sin revisión.
