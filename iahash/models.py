"""Pydantic models shared across the IA-HASH v1.2 stack."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Prompt(BaseModel):
    id: int
    slug: str
    owner_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    full_prompt: Optional[str] = None
    category: Optional[str] = None
    is_master: bool = True
    visibility: str = "public"
    h_public: Optional[str] = None
    h_secret: Optional[str] = None
    signature_prompt: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class PromptSummary(BaseModel):
    slug: str
    title: str
    description: Optional[str] = None
    category: Optional[str] = None


class IAHashDocument(BaseModel):
    protocol_version: str = Field(default="IAHASH-1.2")
    type: str
    mode: str
    prompt_id: Optional[str]
    prompt_hmac_verified: bool
    timestamp: str
    model: str
    h_prompt: str
    h_response: str
    h_total: str
    signature: str
    issuer_id: str
    issuer_pk_url: str
    conversation_url: Optional[str] = None
    provider: Optional[str] = None
    subject_id: Optional[str] = None
    store_raw: bool = False
    raw_prompt_text: Optional[str] = None
    raw_response_text: Optional[str] = None
    iah_id: str


class SequenceStep(BaseModel):
    id: int
    position: int
    title: str
    description: Optional[str] = None
    prompt_id: Optional[int] = None
    prompt_slug: Optional[str] = None


class Sequence(BaseModel):
    id: int
    slug: str
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    visibility: str = "public"
    created_at: Optional[str] = None
    steps: List[SequenceStep] = Field(default_factory=list)


class PairVerificationRequest(BaseModel):
    prompt_text: str
    response_text: str
    prompt_id: Optional[str] = None
    model: str = "unknown"
    subject_id: Optional[str] = None
    store_raw: bool = False


class ConversationVerificationRequest(BaseModel):
    prompt_id: Optional[str] = None
    url: str
    model_override: Optional[str] = None
    store_raw: bool = False


class CheckerRequest(BaseModel):
    document: Dict[str, Any]
