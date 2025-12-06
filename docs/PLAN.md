# IA-HASH Builder v1.0 — Plan de entrega

## Estructura propuesta
- `api/`: FastAPI + routers (`/api/issue`, `/api/verify`, `/api/public-key`, `/api/master-prompts`).
- `iahash/`: librería publicable (crypto, issuer, verifier, models, paths).
- `scripts/`: utilidades CLI (generación de claves, demo offline).
- `web/`: UI estática (emisor, verificador, docs, master prompts).
- `tests/`: unitarios + integración API.
- `docs/`: especificaciones, manuales y notas de producto.

## Próximos pasos sugeridos
1. **Frontend completo**: navegación, descarga de JSON, selector de idioma, landing de master prompts y docs/help.
2. **Docker endurecido**: imagen multistage + notas para reverse proxy TLS (Traefik/Coolify).
3. **Distribución PyPI**: `pyproject.toml`, versionado semántico y publicación automática.
4. **Prompt Library**: CRUD básico y catálogos versionados.
5. **Conversación completa**: soportar `conversation_id` y recuperación de transcripts externos.
6. **Verificación offline**: CLI empaquetada en `iahash` para validar documentos sin red.
