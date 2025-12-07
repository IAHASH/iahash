from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    FileResponse,
)
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from iahash.issuer import issue_pair, issue_conversation, PROTOCOL_VERSION
from iahash.extractors import extract_chatgpt_share
from iahash.extractors.chatgpt_share import (
    ERROR_PARSING,
    ERROR_UNREACHABLE,
    ERROR_UNSUPPORTED,
)
from iahash.verifier import verify_document
from iahash.db import (
    get_prompt_by_slug,
    list_prompts,
    list_sequences,
    get_sequence_by_slug,
    get_iah_document_by_id,
    ensure_db_initialized,
)


APP_NAME = "IA-HASH API"
API_VERSION = "1.2.0"

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"
KEYS_DIR = Path("/data/keys")
PUBLIC_KEY_PATH = KEYS_DIR / "issuer_ed25519.pub"


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class PairIssueRequest(BaseModel):
    prompt_text: str
    response_text: str
    prompt_id: Optional[str] = None
    model: str = "unknown"
    issuer_id: Optional[str] = None
    issuer_pk_url: Optional[str] = None
    subject_id: Optional[str] = None
    store_raw: bool = False


class ConversationIssueRequest(BaseModel):
    prompt_text: str
    response_text: str
    prompt_id: str
    model: str
    conversation_url: str
    provider: str
    issuer_id: Optional[str] = None
    issuer_pk_url: Optional[str] = None
    subject_id: Optional[str] = None
    store_raw: bool = False


class CheckRequest(BaseModel):
    document: Dict[str, Any]


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title=APP_NAME,
    version=API_VERSION,
)


@app.on_event("startup")
def initialize_database() -> None:
    ensure_db_initialized()

# CORS liberal por ahora (podemos afinar luego)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static: /static → carpeta web/ (styles.css, logo.png, etc.)
if WEB_DIR.exists():
    app.mount(
        "/static",
        StaticFiles(directory=str(WEB_DIR), html=False),
        name="static",
    )


# ---------------------------------------------------------------------------
# Root & meta endpoints
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def root() -> HTMLResponse:
    """
    Página principal de IA-HASH.

    Sirve web/index.html. Si por lo que sea no existe,
    devolvemos la info JSON de la API como fallback.
    """
    index_path = WEB_DIR / "index.html"
    if index_path.exists():
        return HTMLResponse(index_path.read_text(encoding="utf-8"))
    # Fallback: igual que /api
    return JSONResponse(api_info())


@app.get("/api", response_class=JSONResponse)
def api_info() -> Dict[str, Any]:
    """Información básica de la API y rutas principales."""
    return {
        "name": APP_NAME,
        "version": API_VERSION,
        "standard": PROTOCOL_VERSION,
        "endpoints": {
            "pair_issue": "/api/verify/pair",
            "conversation_issue": "/api/verify/conversation",
            "check": "/api/check",
            "prompts": "/prompts",
            "sequences": "/sequences",
            "iah_document": "/iah/{iah_id}",
            "public_key": "/public-key",
            "health": "/health",
        },
    }


@app.get("/health", response_class=JSONResponse)
def health() -> Dict[str, str]:
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Public key
# ---------------------------------------------------------------------------

@app.get("/keys/issuer_ed25519.pub")
def get_public_key_pem() -> FileResponse:
    """
    Devuelve la clave pública Ed25519 en PEM.

    Esta ruta es la usada por defecto en issuer.py:
    http://localhost:8000/keys/issuer_ed25519.pub
    """
    if not PUBLIC_KEY_PATH.exists():
        raise HTTPException(status_code=404, detail="Public key not found")
    return FileResponse(
        str(PUBLIC_KEY_PATH),
        media_type="application/x-pem-file",
        filename="issuer_ed25519.pub",
    )


@app.get("/public-key", response_class=JSONResponse)
def get_public_key_info() -> Dict[str, Any]:
    """
    Versión JSON de la clave pública (contenido PEM en texto plano).
    Útil para inspección rápida desde el navegador.
    """
    if not PUBLIC_KEY_PATH.exists():
        raise HTTPException(status_code=404, detail="Public key not found")
    pem_text = PUBLIC_KEY_PATH.read_text(encoding="utf-8")
    return {
        "issuer_pk_url": "/keys/issuer_ed25519.pub",
        "pem": pem_text,
    }


# ---------------------------------------------------------------------------
# Core IA-HASH endpoints
# ---------------------------------------------------------------------------

@app.post("/api/verify/pair", response_class=JSONResponse)
def api_verify_pair(payload: PairIssueRequest) -> Dict[str, Any]:
    """
    Genera un documento IA-HASH para un par prompt + respuesta local.
    """
    doc = issue_pair(
        prompt_text=payload.prompt_text,
        response_text=payload.response_text,
        prompt_id=payload.prompt_id,
        model=payload.model,
        issuer_id=payload.issuer_id,
        issuer_pk_url=payload.issuer_pk_url,
        subject_id=payload.subject_id,
        store_raw=payload.store_raw,
    )
    return doc


@app.post("/api/verify/conversation", response_class=JSONResponse)
def api_verify_conversation(payload: ConversationIssueRequest) -> Dict[str, Any]:
    """
    Genera un documento IA-HASH para una conversación verificada por URL.
    """
    extracted = extract_chatgpt_share(payload.conversation_url)
    if extracted.get("error"):
        error = extracted["error"]
        if error == ERROR_UNREACHABLE:
            detail = "Conversation URL unreachable"
        elif error == ERROR_UNSUPPORTED:
            detail = "Unsupported conversation format"
        elif error == ERROR_PARSING:
            detail = "Unable to parse conversation content"
        else:
            detail = "Unknown extraction error"
        raise HTTPException(status_code=400, detail=detail)

    if (
        extracted["prompt_text"] != payload.prompt_text
        or extracted["response_text"] != payload.response_text
    ):
        raise HTTPException(
            status_code=400, detail="Extracted conversation does not match payload"
        )

    doc = issue_conversation(
        prompt_text=extracted["prompt_text"],
        response_text=extracted["response_text"],
        prompt_id=payload.prompt_id,
        model=extracted.get("model") or payload.model,
        conversation_url=payload.conversation_url,
        provider=extracted.get("provider") or payload.provider,
        issuer_id=payload.issuer_id,
        issuer_pk_url=payload.issuer_pk_url,
        subject_id=payload.subject_id,
        store_raw=payload.store_raw,
    )
    return doc


@app.post("/api/check", response_class=JSONResponse)
def api_check(payload: CheckRequest) -> Dict[str, Any]:
    """
    Verifica un documento IA-HASH completo recibido en el body.
    """
    result = verify_document(payload.document)
    return {
        "document": payload.document,
        "verification": result,
    }


# ---------------------------------------------------------------------------
# Prompts & secuencias
# ---------------------------------------------------------------------------

@app.get("/prompts", response_class=JSONResponse)
def api_list_prompts() -> Dict[str, Any]:
    return {"items": list_prompts()}


@app.get("/prompts/{slug}", response_class=JSONResponse)
def api_get_prompt(slug: str) -> Dict[str, Any]:
    prompt = get_prompt_by_slug(slug)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return prompt


@app.get("/sequences", response_class=JSONResponse)
def api_list_sequences() -> Dict[str, Any]:
    return {"items": list_sequences()}


@app.get("/sequences/{slug}", response_class=JSONResponse)
def api_get_sequence(slug: str) -> Dict[str, Any]:
    sequence = get_sequence_by_slug(slug)
    if not sequence:
        raise HTTPException(status_code=404, detail="Sequence not found")
    return sequence


# ---------------------------------------------------------------------------
# IA-HASH documents
# ---------------------------------------------------------------------------

@app.get("/iah/{iah_id}", response_class=JSONResponse)
def api_get_iah_document(iah_id: str) -> Dict[str, Any]:
    doc = get_iah_document_by_id(iah_id)
    if not doc:
        raise HTTPException(status_code=404, detail="IA-HASH document not found")
    return doc


# ---------------------------------------------------------------------------
# Local dev entrypoint (no se usa en Docker, pero viene bien)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
