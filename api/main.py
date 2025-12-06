from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from iahash.db import (
    get_iah_document_by_id,
    get_prompt_by_slug,
    get_sequence_by_slug,
    list_prompts,
    list_sequences,
)
from iahash.extractors import extract_chatgpt_share
from iahash.issuer import issue_conversation, issue_pair
from iahash.models import (
    CheckerRequest,
    ConversationVerificationRequest,
    PairVerificationRequest,
)
from iahash.verifier import VerificationStatus, verify_document

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"
TEMPLATES = Jinja2Templates(directory=WEB_DIR / "templates")

app = FastAPI(title="IA-HASH v1.2", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=WEB_DIR / "static"), name="static")
app.mount("/docs", StaticFiles(directory=BASE_DIR / "docs"), name="docs")


@app.get("/keys/issuer_ed25519.pub", include_in_schema=False)
def public_key_file():
    key_path = Path("/data/keys/issuer_ed25519.pub")
    if not key_path.exists():
        raise HTTPException(status_code=404, detail="Public key not found")
    return FileResponse(key_path)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home(request: Request):
    prompts = list_prompts()
    sequences = list_sequences()
    return TEMPLATES.TemplateResponse(
        "index.html",
        {"request": request, "prompts": prompts, "sequences": sequences},
    )


@app.get("/prompts", response_class=HTMLResponse, include_in_schema=False)
def prompts_page(request: Request):
    prompts = list_prompts()
    return TEMPLATES.TemplateResponse("prompts.html", {"request": request, "prompts": prompts})


@app.get("/prompts/{slug}", response_class=HTMLResponse, include_in_schema=False)
def prompt_detail_page(slug: str, request: Request):
    prompt = get_prompt_by_slug(slug)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return TEMPLATES.TemplateResponse("prompt_detail.html", {"request": request, "prompt": prompt})


@app.get("/verify", response_class=HTMLResponse, include_in_schema=False)
def verify_page(request: Request):
    prompts = list_prompts()
    return TEMPLATES.TemplateResponse("verify.html", {"request": request, "prompts": prompts})


@app.get("/sequences", response_class=HTMLResponse, include_in_schema=False)
def sequences_page(request: Request):
    sequences = list_sequences()
    return TEMPLATES.TemplateResponse("sequences.html", {"request": request, "sequences": sequences})


@app.get("/sequences/{slug}", response_class=HTMLResponse, include_in_schema=False)
def sequence_detail_page(slug: str, request: Request):
    sequence = get_sequence_by_slug(slug)
    if not sequence:
        raise HTTPException(status_code=404, detail="Sequence not found")
    return TEMPLATES.TemplateResponse("sequence_detail.html", {"request": request, "sequence": sequence})


@app.get("/compare", response_class=HTMLResponse, include_in_schema=False)
def compare_page(request: Request):
    prompts = list_prompts()
    return TEMPLATES.TemplateResponse("compare.html", {"request": request, "prompts": prompts})


@app.get("/docs", response_class=HTMLResponse, include_in_schema=False)
def docs_page(request: Request):
    return TEMPLATES.TemplateResponse("docs.html", {"request": request})


@app.get("/account", response_class=HTMLResponse, include_in_schema=False)
def account_page(request: Request):
    return TEMPLATES.TemplateResponse("account.html", {"request": request})


@app.get("/iah/{iah_id}", response_class=HTMLResponse, include_in_schema=False)
def iah_public_page(iah_id: str, request: Request):
    document = get_iah_document_by_id(iah_id)
    if not document:
        raise HTTPException(status_code=404, detail="IA-HASH not found")
    return TEMPLATES.TemplateResponse("docs.html", {"request": request, "iah": document})


# --- API endpoints (protocol) ---


@app.post("/api/verify/pair")
def api_verify_pair(payload: PairVerificationRequest):
    document = issue_pair(
        prompt_text=payload.prompt_text,
        response_text=payload.response_text,
        prompt_id=payload.prompt_id,
        model=payload.model,
        subject_id=payload.subject_id,
        store_raw=payload.store_raw,
    )
    return {"status": VerificationStatus.VALID, "document": document}


@app.post("/api/verify/conversation")
def api_verify_conversation(payload: ConversationVerificationRequest):
    extraction = extract_chatgpt_share(payload.url)
    if extraction.get("error"):
        return JSONResponse({"status": extraction["error"], "message": "Unable to process conversation"}, status_code=400)

    document = issue_conversation(
        prompt_text=extraction["prompt_text"],
        response_text=extraction["response_text"],
        prompt_id=payload.prompt_id,
        model=payload.model_override or extraction.get("model", "unknown"),
        conversation_url=extraction.get("conversation_url", payload.url),
        provider=extraction.get("provider", "chatgpt"),
        store_raw=payload.store_raw,
    )
    return {"status": VerificationStatus.VALID, "document": document}


@app.post("/api/check")
def api_check(payload: CheckerRequest):
    result = verify_document(payload.document)
    return result


@app.get("/api/iah/{iah_id}")
def api_get_iah(iah_id: str):
    document = get_iah_document_by_id(iah_id)
    if not document:
        raise HTTPException(status_code=404, detail="IA-HASH not found")
    # Do not expose raw contents by default
    document_filtered = {k: v for k, v in document.items() if not k.startswith("raw_") or document.get("store_raw")}
    return document_filtered


@app.get("/api/prompts")
def api_prompts():
    return {"prompts": list_prompts()}


@app.get("/api/prompts/{slug}")
def api_prompt_detail(slug: str):
    prompt = get_prompt_by_slug(slug)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return prompt


@app.get("/api/sequences")
def api_sequences():
    return {"sequences": list_sequences()}


@app.get("/api/sequences/{slug}")
def api_sequence_detail(slug: str):
    sequence = get_sequence_by_slug(slug)
    if not sequence:
        raise HTTPException(status_code=404, detail="Sequence not found")
    return sequence
