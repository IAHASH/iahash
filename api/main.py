from fastapi import FastAPI
from pydantic import BaseModel

from iahash.issuer import issue_document
from iahash.verifier import verify_document
from iahash.models import IAHashDocument

app = FastAPI(
    title="IA-HASH API",
    version="0.1.0",
    description="Issue and verify IA-HASH documents (Prompt + Response → Verifiable).",
)


class IssuePayload(BaseModel):
    prompt_maestro: str
    respuesta: str
    modelo: str = "unknown"
    prompt_id: str | None = None
    subject_id: str | None = None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/issue", response_model=IAHashDocument)
def issue(payload: IssuePayload):
    doc = issue_document(
        prompt_text=payload.prompt_maestro,
        respuesta_text=payload.respuesta,
        modelo=payload.modelo,
        prompt_id=payload.prompt_id,
        subject_id=payload.subject_id,
    )
    return doc


@app.post("/verify")
def verify(doc: IAHashDocument):
    valid, reason = verify_document(doc)
    return {"valid": valid, "reason": reason}
