from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, HttpUrl

from iahash.db import (
    create_sequence,
    ensure_db_initialized,
    get_iah_document_by_id,
    get_prompt_by_slug,
    get_sequence_by_slug,
    list_prompts,
    list_sequences,
)
from iahash.config import ISSUER_PK_URL
from iahash.crypto import get_issuer_public_key_pem
from iahash.extractors.chatgpt_share import extract_payload_from_chatgpt_share
from iahash.issuer import PROTOCOL_VERSION, issue_conversation, issue_from_share, issue_pair
from iahash.verifier import verify_document

APP_NAME = "IA-HASH API"
API_VERSION = "1.2.0"
API_DESCRIPTION = "IA-HASH verification service"

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"
templates = Jinja2Templates(directory=str(WEB_DIR / "templates"))


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


class IssueFromSharePayload(BaseModel):
    share_url: HttpUrl
    model: str | None = "chatgpt"
    prompt_id: str | None = None
    subject_id: str | None = None


class SequenceStepPayload(BaseModel):
    title: str
    description: Optional[str] = None
    prompt_id: Optional[int] = None
    position: Optional[int] = None
    model: str = "unknown"


class SequencePayload(BaseModel):
    slug: str
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    visibility: str = "public"
    steps: Optional[list[SequenceStepPayload]] = None


app = FastAPI(title=APP_NAME, version=API_VERSION, description=API_DESCRIPTION)

app.mount("/static", StaticFiles(directory="web/static"), name="static")


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


@app.get("/", response_class=HTMLResponse)
def web_home(request: Request) -> Any:
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/verify", response_class=HTMLResponse)
def web_verify(request: Request) -> Any:
    return templates.TemplateResponse("verify.html", {"request": request})


@app.get("/compare", response_class=HTMLResponse)
def web_compare(request: Request) -> Any:
    return templates.TemplateResponse("compare.html", {"request": request})


@app.get("/docs", response_class=HTMLResponse)
def web_docs(request: Request) -> Any:
    return templates.TemplateResponse("docs.html", {"request": request})


@app.get("/account", response_class=HTMLResponse)
def web_account(request: Request) -> Any:
    return templates.TemplateResponse("account.html", {"request": request})


@app.get("/prompts", response_class=HTMLResponse)
def web_prompts(request: Request) -> Any:
    prompts = list_prompts()
    return templates.TemplateResponse(
        "prompts.html", {"request": request, "prompts": prompts}
    )


@app.get("/prompts/{slug}", response_class=HTMLResponse)
def web_prompt_detail(slug: str, request: Request) -> Any:
    prompt = get_prompt_by_slug(slug)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    prompt = {**prompt, "h_secret": None}
    return templates.TemplateResponse(
        "prompt_detail.html", {"request": request, "prompt": prompt}
    )


@app.get("/sequences", response_class=HTMLResponse)
def web_sequences(request: Request) -> Any:
    sequences = list_sequences()
    return templates.TemplateResponse(
        "sequences.html", {"request": request, "sequences": sequences}
    )


@app.get("/sequences/new", response_class=HTMLResponse)
def web_sequences_new(request: Request) -> Any:
    prompts = list_prompts()
    return templates.TemplateResponse(
        "sequence_create.html", {"request": request, "prompts": prompts}
    )


@app.get("/sequences/{slug}", response_class=HTMLResponse)
def web_sequence_detail(slug: str, request: Request) -> Any:
    sequence = get_sequence_by_slug(slug)
    if not sequence:
        raise HTTPException(status_code=404, detail="Sequence not found")
    return templates.TemplateResponse(
        "sequence_detail.html", {"request": request, "sequence": sequence}
    )


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
            "issuer_public_key_file": "/keys/issuer_ed25519.pub",
            "health": "/health",
        },
    }


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/keys/issuer_ed25519.pub", response_class=PlainTextResponse)
def serve_issuer_public_key() -> str:
    try:
        pem_bytes = get_issuer_public_key_pem()
    except FileNotFoundError as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=404, detail="Public key not found") from exc

    return pem_bytes.decode("utf-8")


@app.get("/public-key")
def get_public_key() -> Dict[str, str]:
    pem_bytes = get_issuer_public_key_pem()
    pem_text = pem_bytes.decode("utf-8")
    key_hex = pem_bytes.hex()

    return {
        "issuer_pk_url": ISSUER_PK_URL,
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


@app.post("/api/issue-from-share")
async def api_issue_from_share(payload: IssueFromSharePayload) -> Dict[str, Any]:
    async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
        response = await client.get(str(payload.share_url))

    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Cannot fetch ChatGPT share URL")

    soup = BeautifulSoup(response.text, "html.parser")
    script = soup.find("script", id="__NEXT_DATA__")
    if not script or not script.string:
        raise HTTPException(status_code=400, detail="ChatGPT share page has no data to parse")

    try:
        data = json.loads(script.string)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Cannot parse ChatGPT share payload") from exc

    try:
        payload_extracted = extract_payload_from_chatgpt_share(data)
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    prompt_text = payload_extracted.get("prompt_text")
    response_text = payload_extracted.get("response_text")
    model_value = payload_extracted.get("model") or payload.model or "chatgpt"

    if not prompt_text or not response_text:
        raise HTTPException(status_code=400, detail="No se pudo extraer prompt o respuesta")

    try:
        return issue_from_share(
            prompt_text=prompt_text,
            response_text=response_text,
            model=model_value,
            share_url=str(payload.share_url),
            prompt_id=payload.prompt_id,
            subject_id=payload.subject_id,
        )
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/prompts")
def api_list_prompts() -> Dict[str, Any]:
    return {"prompts": list_prompts()}


@app.get("/api/prompts/{slug}")
def api_get_prompt(slug: str) -> Dict[str, Any]:
    prompt = get_prompt_by_slug(slug)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    prompt = {**prompt, "h_secret": None}
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


@app.post("/api/sequences")
def api_create_sequence(payload: SequencePayload) -> Dict[str, Any]:
    try:
        create_sequence(
            slug=payload.slug,
            title=payload.title,
            description=payload.description,
            category=payload.category,
            visibility=payload.visibility,
            steps=[step.dict() for step in payload.steps or []],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    sequence = get_sequence_by_slug(payload.slug)
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
