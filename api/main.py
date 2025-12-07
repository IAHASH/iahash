from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    FileResponse,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
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
TEMPLATES_DIR = WEB_DIR / "templates"
KEYS_DIR = Path("/data/keys")
PUBLIC_KEY_PATH = KEYS_DIR / "issuer_ed25519.pub"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


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


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title=APP_NAME,
    version=API_VERSION,
)


"""
Inicialización temprana de la base de datos.

`TestClient(app)` de Starlette no siempre ejecuta los eventos de startup
cuando no se usa como contexto, así que inicializamos aquí para que los
tests y scripts tengan el esquema disponible incluso sin lifecycle events.
"""
ensure_db_initialized()


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

# Static: /static → carpeta web/static (styles.css, logo.png, etc.)
static_dir = WEB_DIR / "static"
if static_dir.exists():
    app.mount(
        "/static",
        StaticFiles(directory=str(static_dir), html=False),
        name="static",
    )


# ---------------------------------------------------------------------------
# Root & meta endpoints
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def root(request: Request) -> HTMLResponse:
    """
    Página principal de IA-HASH.

    Sirve web/index.html. Si por lo que sea no existe,
    devolvemos la info JSON de la API como fallback.
    """
    if (TEMPLATES_DIR / "index.html").exists():
        return templates.TemplateResponse("index.html", {"request": request})
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
    try:
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
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=400, detail=str(exc))


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

    prompt_text = extracted.get("prompt_text")
    response_text = extracted.get("response_text")

    if not prompt_text or not response_text:
        raise HTTPException(status_code=400, detail="Conversation content unavailable")

    if payload.prompt_text:
        if extracted["prompt_text"] != payload.prompt_text:
            raise HTTPException(
                status_code=400,
                detail="Extracted prompt does not match payload",
            )
        prompt_text = payload.prompt_text

    if payload.response_text:
        if extracted["response_text"] != payload.response_text:
            raise HTTPException(
                status_code=400,
                detail="Extracted response does not match payload",
            )
        response_text = payload.response_text

    try:
        doc = issue_conversation(
            prompt_text=prompt_text,
            response_text=response_text,
            prompt_id=payload.prompt_id,
            model=extracted.get("model") or payload.model or "unknown",
            conversation_url=payload.conversation_url,
            provider=extracted.get("provider") or payload.provider or "unknown",
            issuer_id=payload.issuer_id,
            issuer_pk_url=payload.issuer_pk_url,
            subject_id=payload.subject_id,
            store_raw=payload.store_raw,
        )
        return doc
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=400, detail=str(exc))


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


@app.get("/verify", response_class=HTMLResponse)
def web_verify(request: Request) -> HTMLResponse:
    prompts = list_prompts()
    return templates.TemplateResponse(
        "verify.html", {"request": request, "prompts": prompts}
    )


@app.get("/compare", response_class=HTMLResponse)
def web_compare(request: Request) -> HTMLResponse:
    prompts = list_prompts()
    return templates.TemplateResponse(
        "compare.html", {"request": request, "prompts": prompts}
    )


# ---------------------------------------------------------------------------
# Prompts & secuencias
# ---------------------------------------------------------------------------

@app.get("/prompts", response_class=HTMLResponse)
def web_list_prompts(request: Request) -> HTMLResponse:
    prompts = list_prompts()
    return templates.TemplateResponse(
        "prompts.html", {"request": request, "prompts": prompts}
    )


@app.get("/prompts/{slug}", response_class=HTMLResponse)
def web_get_prompt(request: Request, slug: str) -> HTMLResponse:
    prompt = get_prompt_by_slug(slug)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    prompt["body"] = prompt.get("full_prompt")
    return templates.TemplateResponse(
        "prompt_detail.html", {"request": request, "prompt": prompt}
    )


@app.get("/sequences", response_class=HTMLResponse)
def web_list_sequences(request: Request) -> HTMLResponse:
    sequences = list_sequences()
    return templates.TemplateResponse(
        "sequences.html", {"request": request, "sequences": sequences}
    )


@app.get("/sequences/{slug}", response_class=HTMLResponse)
def web_get_sequence(request: Request, slug: str) -> HTMLResponse:
    sequence = get_sequence_by_slug(slug)
    if not sequence:
        raise HTTPException(status_code=404, detail="Sequence not found")
    return templates.TemplateResponse(
        "sequence_detail.html", {"request": request, "sequence": sequence}
    )


# ---------------------------------------------------------------------------
# IA-HASH documents
# ---------------------------------------------------------------------------

@app.get("/iah/{iah_id}", response_class=HTMLResponse)
def web_get_iah_document(request: Request, iah_id: str) -> HTMLResponse:
    doc = get_iah_document_by_id(iah_id)
    if not doc:
        raise HTTPException(status_code=404, detail="IA-HASH document not found")
    return templates.TemplateResponse("docs.html", {"request": request, "iah": doc})


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
