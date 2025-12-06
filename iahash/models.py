from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class LLMID(BaseModel):
    """Extended identity for the model that generated the output."""

    model_config = ConfigDict(extra="forbid")

    name: str
    version: Optional[str] = None
    provider: Optional[str] = None
    build_id: Optional[str] = None
    params: dict = Field(default_factory=dict)


class IAHashDocument(BaseModel):
    """Canonical IA-HASH document schema."""

    model_config = ConfigDict(extra="forbid")

    version: str = "IAHASH-1"
    prompt_id: Optional[str] = None
    prompt_maestro: str
    respuesta: str
    modelo: str = "unknown"
    timestamp: str
    subject: Optional[str] = None
    conversation_id: Optional[str] = Field(
        default=None,
        description="Optional conversation identifier for multi-turn exchanges.",
    )
    llmid: Optional[LLMID] = Field(default=None, description="Extended model identity")
    metadata: dict = Field(default_factory=dict)

    h_prompt: str
    h_respuesta: str
    h_contexto: str
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
    subject: Optional[str] = None
    conversation_id: Optional[str] = None
    llmid: Optional[LLMID] = None
    contexto: Optional[str] = Field(default=None, description="Context string to bind")
    metadata: dict = Field(default_factory=dict)
