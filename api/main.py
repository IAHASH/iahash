from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from iahash.issuer import issue_document
from iahash.verifier import verify_document
from iahash.models import IAHashDocument
from iahash.paths import public_key_path

WEB_DIR = Path(__file__).parent.parent / "web"


def ensure_keys_exist(path: Path = public_key_path()) -> Path:
    if not path.exists():
        raise HTTPException(status_code=500, detail="Public key not found. Generate keys first.")
    return path


class IssuePayload(BaseModel):
    prompt_maestro: str = Field(..., description="Texto exacto enviado a la IA")
    respuesta: str = Field(..., description="Respuesta completa devuelta por la IA")
    modelo: str = Field("unknown", description="Modelo utilizado: gpt-5, claude-3, etc.")
    prompt_id: str | None = Field(None, description="Identificador lógico del prompt maestro")
    subject_id: str | None = Field(None, description="Identificador del sujeto/usuario")
    conversation_id: str | None = Field(
        None, description="Conversación completa (reservado para módulo futuro)"
    )


class VerifyResponse(BaseModel):
    valid: bool
    reason: str


router = APIRouter(prefix="/api", tags=["IA-HASH"])


@router.get("/health", summary="Healthcheck")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/issue", response_model=IAHashDocument, summary="Emitir IA-HASH")
def issue(payload: IssuePayload) -> IAHashDocument:
    doc = issue_document(
        prompt_text=payload.prompt_maestro,
        respuesta_text=payload.respuesta,
        modelo=payload.modelo,
        prompt_id=payload.prompt_id,
        subject_id=payload.subject_id,
        conversation_id=payload.conversation_id,
    )
    return doc


@router.post("/verify", response_model=VerifyResponse, summary="Verificar IA-HASH")
def verify(doc: IAHashDocument) -> VerifyResponse:
    valid, reason = verify_document(doc)
    return VerifyResponse(valid=valid, reason=reason)


@router.get(
    "/public-key",
    summary="Obtener clave pública",
    response_class=PlainTextResponse,
    responses={200: {"description": "PEM"}},
)
def public_key(path: Annotated[Path, Depends(ensure_keys_exist)]) -> str:
    return path.read_text()


MASTER_PROMPTS = [
    {
        "id": "cv-honesto-v1",
        "title": "CV Honesto",
        "language": "es",
        "description": "Plantilla para crear un CV transparente con logros verificables.",
        "prompt": "Redacta un CV honesto resaltando logros verificables y omitiendo exageraciones.",
    },
    {
        "id": "analisis-psicologico-v1",
        "title": "Análisis psicológico rápido",
        "language": "es",
        "description": "Guía para un análisis psicológico breve sin diagnóstico clínico.",
        "prompt": "Analiza el siguiente texto desde la perspectiva emocional y de sesgos cognitivos.",
    },
    {
        "id": "auto-evaluacion-profesional-v1",
        "title": "Autoevaluación profesional",
        "language": "es",
        "description": "Checklist para evaluar desempeño profesional y áreas de mejora.",
        "prompt": "Evalúa fortalezas, áreas de mejora y siguientes pasos en la trayectoria profesional.",
    },
]


@router.get("/master-prompts", summary="Listado de prompts maestros")
def master_prompts() -> list[dict[str, str]]:
    return MASTER_PROMPTS


app = FastAPI(
    title="IA-HASH API",
    version="0.2.0",
    description="Issue and verify IA-HASH documents (Prompt + Response → Verifiable).",
    contact={"name": "IA-HASH", "url": "https://github.com/IAHASH/iahash"},
)

app.include_router(router)


@app.get("/", include_in_schema=False)
def serve_index():
    return FileResponse(WEB_DIR / "index.html")


app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
