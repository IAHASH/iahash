from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from iahash.issuer import issue_document
from iahash.models import IAHashDocument, IssueFromTextRequest, LLMID
from iahash.paths import public_key_path
from iahash.prompts import (
    MasterPrompt,
    MasterPromptSummary,
    get_master_prompt,
    list_master_prompts,
    save_custom_prompt,
)
from iahash.verifier import verify_document

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


class VerifyResponse(BaseModel):
    valid: bool
    reason: str


class IssuePayload(IssueFromTextRequest):
    prompt_maestro: str = Field(..., description="Texto exacto enviado a la IA")
    respuesta: str = Field(..., description="Respuesta completa devuelta por la IA")
    modelo: str | None = Field(None, description="Modelo utilizado: gpt-5, claude-3, etc.")
    llmid: LLMID | None = None
    contexto: str | None = Field(None, description="Contexto adicional a normalizar")
    metadata: dict = Field(default_factory=dict)


class MasterPromptCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Identificador estable (PROMPT-ID)")
    title: str
    version: str
    language: str = "es"
    category: str | None = None
    description: str | None = None
    body: str
    metadata: dict = Field(default_factory=dict)
    prompt_hash: str | None = Field(
        default=None,
        description="Hash opcional si ya está calculado. Si falta, se calcula automáticamente.",
    )


def ensure_public_key(path: Path = public_key_path()) -> Path:
    if not path.exists():
        raise HTTPException(status_code=500, detail="Public key not found. Generate keys first.")
    return path


app = FastAPI(
    title="IA-HASH API",
    description="Issue and verify IA-HASH documents (Prompt + Response → Verifiable).",
    version="0.3.0",
    contact={"name": "IA-HASH", "url": "https://github.com/IAHASH/iahash"},
    license_info={"name": "Apache-2.0", "url": "https://www.apache.org/licenses/LICENSE-2.0"},
    openapi_tags=[{"name": "IA-HASH", "description": "Issue and verify IA-HASH documents."}],
)


@app.get("/health", tags=["IA-HASH"], summary="Healthcheck")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/issue", response_model=IAHashDocument, tags=["IA-HASH"], summary="Emitir IA-HASH")
def issue(payload: IssuePayload) -> IAHashDocument:
    doc = issue_document(
        prompt_text=payload.prompt_maestro,
        respuesta_text=payload.respuesta,
        modelo=payload.modelo,
        prompt_id=payload.prompt_id,
        subject=payload.subject,
        conversation_id=payload.conversation_id,
        llmid=payload.llmid,
        metadata=payload.metadata,
        contexto=payload.contexto,
    )
    return doc


@app.post("/verify", response_model=VerifyResponse, tags=["IA-HASH"], summary="Verificar IA-HASH")
def verify(doc: IAHashDocument) -> VerifyResponse:
    valid, reason = verify_document(doc)
    return VerifyResponse(valid=valid, reason=reason)


@app.get(
    "/public-key",
    summary="Obtener clave pública",
    response_class=PlainTextResponse,
    responses={200: {"description": "PEM"}},
    tags=["IA-HASH"],
)
def public_key(path: Annotated[Path, Depends(ensure_public_key)]) -> str:
    return path.read_text()


@app.get(
    "/master-prompts",
    tags=["IA-HASH"],
    summary="Listado de prompts maestros",
    response_model=list[MasterPromptSummary],
)
def master_prompts() -> list[MasterPromptSummary]:
    return list_master_prompts()


@app.get(
    "/master-prompts/{prompt_id}",
    tags=["IA-HASH"],
    summary="Detalle de prompt maestro incluyendo hash",
    response_model=MasterPrompt,
)
def master_prompt_detail(prompt_id: str) -> MasterPrompt:
    prompt = get_master_prompt(prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt maestro no encontrado")
    return prompt


@app.post(
    "/master-prompts",
    tags=["IA-HASH"],
    summary="Crear o actualizar un prompt maestro",
    status_code=201,
    response_model=MasterPrompt,
)
def master_prompt_create(payload: MasterPromptCreate) -> MasterPrompt:
    return save_custom_prompt(payload.model_dump())


@app.get("/", include_in_schema=False)
def serve_index():
    return FileResponse(WEB_DIR / "index.html")


app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
