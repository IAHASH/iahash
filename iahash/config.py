from __future__ import annotations
import os

# URL base de IA-HASH (para futuros usos)
IAHASH_BASE_URL = os.getenv("IAHASH_BASE_URL", "https://iahash.com")

# URL pública de la clave del emisor utilizada en los documentos IA-HASH
ISSUER_PK_URL = os.getenv(
    "IAHASH_ISSUER_PK_URL",
    f"{IAHASH_BASE_URL}/keys/issuer_ed25519.pub",
)
