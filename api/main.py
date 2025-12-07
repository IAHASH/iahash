from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from iahash.db import (
    ensure_db_initialized,
    get_iah_document_by_id,
    get_prompt_by_slug,
    get_sequence_by_slug,
    list_prompts,
    list_sequences,
)
from iahash.issuer import PROTOCOL_VERSION, issue_conversation, issue_pair
from iahash.verifier import verify_document

APP_NAME = "IA-HASH API"
API_VERSION = "1.2.0"
API_DESCRIPTION = "IA-HASH verification service"

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"
KEYS_DIR = Path("/data/keys")
PUBLIC_KEY_PATH = KEYS_DIR / "issuer_ed25519.pub"


class IssuePairRequest(BaseModel):
    prompt_text: str
    response_text: str
    prompt_id: Optional[str] = None
    model: str = "unknown"
    issuer_id: Optional[str] = None
    issuer_pk_url: Optional[str] = None
    subject_id: Optional[str] = None
    store_raw: bool = False


class IssueConversationRequest(BaseModel):
    prompt_text: Optional[str] = None
    response_text: Optional[str] = None
    prompt_id: Optional[str] = None
    model: str = "unknown"
    conversation_url: str
    provider: Optional[str] = None
    issuer_id: Optional[str] = None
    issuer_pk_url: Optional[str] = None
    subject_id: Optional[str] = None
    store_raw: bool = False


class CheckRequest(BaseModel):
    document: Dict[str, Any]


app = FastAPI(title=APP_NAME, version=API_VERSION, description=API_DESCRIPTION)

# Ensure DB is ready for tests and scripts that do not trigger startup events.
ensure_db_initialized()


@app.on_event("startup")
def initialize_database() -> None:
    ensure_db_initialized()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = WEB_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir), html=False), name="static")


@app.get("/api")
def api_info() -> Dict[str, Any]:
    return {
        "name": APP_NAME,
        "version": API_VERSION,
        "description": API_DESCRIPTION,
        "standard": PROTOCOL_VERSION,
        "endpoints": {
            "pair_issue": "/api/verify/pair",
            "conversation_issue": "/api/verify/conversation",
            "check": "/api/check",
            "prompts": "/api/prompts",
            "prompt": "/api/prompts/{slug}",
            "sequences": "/api/sequences",
            "sequence": "/api/sequences/{slug}",
            "iah_document": "/api/iah/{iah_id}",
            "public_key": "/public-key",
            "health": "/health",
        },
    }


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/public-key")
def get_public_key() -> Dict[str, str]:
    if not PUBLIC_KEY_PATH.exists():
        raise HTTPException(status_code=404, detail="Public key not found")

    pem_text = PUBLIC_KEY_PATH.read_text(encoding="utf-8")
    key_hex = PUBLIC_KEY_PATH.read_bytes().hex()

    return {
        "issuer_pk_url": "/keys/issuer_ed25519.pub",
        "pem": pem_text,
        "hex": key_hex,
    }


@app.post("/api/verify/pair")
def api_verify_pair(payload: IssuePairRequest) -> Dict[str, Any]:
    try:
        return issue_pair(
            prompt_text=payload.prompt_text,
            response_text=payload.response_text,
            prompt_id=payload.prompt_id,
            model=payload.model,
            issuer_id=payload.issuer_id,
            issuer_pk_url=payload.issuer_pk_url,
            subject_id=payload.subject_id,
            store_raw=payload.store_raw,
        )
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/verify/conversation")
def api_verify_conversation(payload: IssueConversationRequest) -> Dict[str, Any]:
    try:
        return issue_conversation(
            prompt_text=payload.prompt_text,
            response_text=payload.response_text,
            prompt_id=payload.prompt_id,
            model=payload.model,
            conversation_url=payload.conversation_url,
            provider=payload.provider,
            issuer_id=payload.issuer_id,
            issuer_pk_url=payload.issuer_pk_url,
            subject_id=payload.subject_id,
            store_raw=payload.store_raw,
        )
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/check")
def api_check(payload: CheckRequest) -> Dict[str, Any]:
    verification = verify_document(payload.document)
    return {"document": payload.document, "verification": verification}


@app.get("/api/prompts")
def api_list_prompts() -> Dict[str, Any]:
    return {"prompts": list_prompts()}


@app.get("/api/prompts/{slug}")
def api_get_prompt(slug: str) -> Dict[str, Any]:
    prompt = get_prompt_by_slug(slug)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return {"prompt": prompt}


@app.get("/api/sequences")
def api_list_sequences() -> Dict[str, Any]:
    return {"sequences": list_sequences()}


@app.get("/api/sequences/{slug}")
def api_get_sequence(slug: str) -> Dict[str, Any]:
    sequence = get_sequence_by_slug(slug)
    if not sequence:
        raise HTTPException(status_code=404, detail="Sequence not found")
    return {"sequence": sequence}


@app.get("/api/iah/{iah_id}")
def api_get_iah_document(iah_id: str) -> Dict[str, Any]:
    document = get_iah_document_by_id(iah_id)
    if not document:
        raise HTTPException(status_code=404, detail="IA-HASH document not found")
    return {"iah": document}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)
