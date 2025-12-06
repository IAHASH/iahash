from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class IAHashDocument(BaseModel):
    """Canonical IA-HASH document schema."""

    model_config = ConfigDict(extra="forbid")

    version: str = "IAHASH-1"
    prompt_id: Optional[str] = None
    prompt_maestro: str
    respuesta: str
    modelo: str = "unknown"
    timestamp: str
    subject_id: Optional[str] = None
    conversation_id: Optional[str] = Field(
        default=None,
        description="Optional conversation identifier for multi-turn exchanges.",
    )

    h_prompt: str
    h_respuesta: str
    h_total: str
    firma_total: str

    issuer_id: str = "iahash.com"
    issuer_pk_url: Optional[str] = None


class IssueFromTextRequest(BaseModel):
    """Input payload for issuing an IA-HASH document directly from raw text."""

    model_config = ConfigDict(extra="forbid")

    prompt_maestro: str
    respuesta: str
    modelo: Optional[str] = None
    prompt_id: Optional[str] = None
    subject_id: Optional[str] = None
    conversation_id: Optional[str] = None
