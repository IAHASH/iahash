# api/main.py
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Any, Dict

from iahash.issuer import (
    issue_pair,
    issue_conversation,
)
from iahash.verifier import verify_document
from iahash.crypto import DEFAULT_PUBLIC_KEY_PATH


# ============================================================================
# FastAPI
# ============================================================================

app = FastAPI(
    title="IA-HASH API",
    version="1.2.0",
    description="API oficial de emisión y verificación IA-HASH v1.2",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# MODELOS
# ============================================================================

class IssuePairRequest(BaseModel):
    prompt: str
    response: str
    prompt_id: Optional[str] = None
    model: str = "unknown"
    issuer_id: Optional[str] = None
    issuer_pk_url: Optional[str] = None
    subject_id: Optional[str] = None
    store_raw: bool = False


class IssueConversationRequest(BaseModel):
    prompt: str
    response: str
    prompt_id: Optional[str] = None
    model: str = "unknown"
    conversation_url: str
    provider: str
    issuer_id: Optional[str] = None
    issuer_pk_url: Optional[str] = None
    subject_id: Optional[str] = None
    store_raw: bool = False


class VerifyRequest(BaseModel):
    document: Dict[str, Any]


# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/public-key")
def public_key():
    return {
        "path": str(DEFAULT_PUBLIC_KEY_PATH),
        "public_key_pem": DEFAULT_PUBLIC_KEY_PATH.read_text(),
    }


@app.post("/api/verify/pair")
def api_issue_pair(body: IssuePairRequest):

    if not body.prompt.strip():
        raise HTTPException(400, "Prompt vacío")
    if not body.response.strip():
        raise HTTPException(400, "Respuesta vacía")

    document = issue_pair(
        prompt_text=body.prompt,
        response_text=body.response,
        prompt_id=body.prompt_id,
        model=body.model,
        issuer_id=body.issuer_id,
        issuer_pk_url=body.issuer_pk_url,
        subject_id=body.subject_id,
        store_raw=body.store_raw,
    )

    return document


@app.post("/api/verify/conversation")
def api_issue_conversation(body: IssueConversationRequest):

    if not body.prompt.strip():
        raise HTTPException(400, "Prompt vacío")
    if not body.response.strip():
        raise HTTPException(400, "Respuesta vacía")

    document = issue_conversation(
        prompt_text=body.prompt,
        response_text=body.response,
        prompt_id=body.prompt_id,
        model=body.model,
        conversation_url=body.conversation_url,
        provider=body.provider,
        issuer_id=body.issuer_id,
        issuer_pk_url=body.issuer_pk_url,
        subject_id=body.subject_id,
        store_raw=body.store_raw,
    )

    return document


@app.post("/api/check")
def api_check(body: VerifyRequest):
    return verify_document(body.document)


@app.get("/")
def root():
    return {
        "name": "IA-HASH API",
        "version": "1.2.0",
        "endpoints": {
            "pair_issue": "/api/verify/pair",
            "conversation_issue": "/api/verify/conversation",
            "check": "/api/check",
            "public_key": "/public-key",
            "health": "/health",
        },
    }
