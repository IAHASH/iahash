"""IA-HASH core package.

Provides utilities to issue and verify IA-HASH documents:
Prompt + Response → Hashed → Signed → Verifiable.
"""

from . import crypto, issuer, models, prompts, verifier
from .issuer import issue_document
from .models import IAHashDocument, LLMID
from .prompts import MasterPrompt, MasterPromptSummary
from .verifier import verify_document

__all__ = [
    "crypto",
    "models",
    "issuer",
    "prompts",
    "verifier",
    "issue_document",
    "verify_document",
    "IAHashDocument",
    "LLMID",
    "MasterPrompt",
    "MasterPromptSummary",
]
__version__ = "0.3.0"
