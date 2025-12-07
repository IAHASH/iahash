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

# URL pública de la clave del emisor utilizada en los documentos IA-HASH
ISSUER_PK_URL = os.getenv(
    "IAHASH_ISSUER_PK_URL",
    f"{IAHASH_BASE_URL}/keys/issuer_ed25519.pub",
)
