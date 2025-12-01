from pydantic import BaseModel


class IAHashDocument(BaseModel):
    version: str = "IA-HASH-1"
    prompt_id: str | None = None
    prompt_maestro: str
    respuesta: str
    modelo: str
    timestamp: str
    subject_id: str | None = None

    h_prompt: str
    h_respuesta: str
    h_total: str
    firma_total: str

    issuer_id: str = "ia-hash.com"
    issuer_pk_url: str | None = None
