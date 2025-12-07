"""IA-HASH v1.2 core package.

Este paquete contiene la lógica principal de IA-HASH:

- iahash.crypto   → primitivas criptográficas, normalización, hashes, firmas, iah_id
- iahash.db       → helpers SQLite para prompts, secuencias y documentos IA-HASH
- iahash.issuer   → emisión de documentos IA-HASH (PAIR / CONVERSATION)
- iahash.models   → modelos Pydantic compartidos
- iahash.verifier → verificación de documentos IA-HASH
"""

from __future__ import annotations

from . import crypto, db, issuer, models, verifier  # imports relativos

__all__ = ["crypto", "db", "issuer", "models", "verifier"]
__version__ = "1.2.0"
