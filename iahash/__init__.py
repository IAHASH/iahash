"""IA-HASH core package.

Provides utilities to issue and verify IA-HASH documents:
Prompt + Response → Hashed → Signed → Verifiable.
"""

from . import crypto, issuer, models, verifier
from .issuer import issue_document
from .models import IAHashDocument
from .verifier import verify_document

__all__ = ["crypto", "models", "issuer", "verifier", "issue_document", "verify_document", "IAHashDocument"]
__version__ = "0.2.0"
