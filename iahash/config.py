from __future__ import annotations
import os

# URL base de IA-HASH (para futuros usos)
#
# Se apunta al dominio oficial si se define ``IAHASH_BASE_URL``. Para
# entornos locales se usa ``http://localhost:8000`` como valor por defecto
# para que los artefactos IA-HASH generados apunten al propio servidor en
# ejecución.
IAHASH_BASE_URL = os.getenv("IAHASH_BASE_URL", "http://localhost:8000")

# Identificador del emisor local utilizado en los documentos IA-HASH
ISSUER_ID = os.getenv("IAHASH_ISSUER_ID", "iahash.local")

# URL pública de la clave del emisor utilizada en los documentos IA-HASH.
#
# Se usa la PK oficial de IA-HASH por defecto, pero se puede sobreescribir con
# IAHASH_ISSUER_PK_URL para entornos locales (ej. iahash.local). Esta URL NO es
# una URL de conversación: apunta al PEM público del emisor.
_env_pk_url = os.getenv("IAHASH_ISSUER_PK_URL")
if _env_pk_url is not None and not _env_pk_url.strip():
    _env_pk_url = None

DEFAULT_ISSUER_PK_URL = "https://iahash.com/keys/issuer_ed25519.pub"
ISSUER_PK_URL = _env_pk_url or DEFAULT_ISSUER_PK_URL
