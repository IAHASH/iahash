from datetime import datetime, timezone
from pathlib import Path

from .crypto import normalise, sha256_hex, load_private_key, sign_hex
from .models import IAHashDocument

KEYS_DIR = Path("keys")
SK_PATH = KEYS_DIR / "iah_sk.pem"


def issue_document(
    prompt_text: str,
    respuesta_text: str,
    modelo: str,
    prompt_id: str | None = None,
    subject_id: str | None = None,
    timestamp: str | None = None,
    issuer_pk_url: str | None = "https://iahash.com/public-key.pem",
    issuer_id: str = "iahash.com",
) -> IAHashDocument:
    """
    Create a signed IA-HASH document for the given prompt + response.
    """

    if timestamp is None:
        timestamp = datetime.now(timezone.utc).isoformat()

    h_prompt = sha256_hex(normalise(prompt_text))
    h_respuesta = sha256_hex(normalise(respuesta_text))

    version = "IA-HASH-1"
    cadena_total = "|".join(
        [version, prompt_id or "", h_prompt, h_respuesta, modelo, timestamp]
    )
    h_total = sha256_hex(cadena_total.encode("utf-8"))

    sk = load_private_key(SK_PATH)
    firma_total = sign_hex(h_total, sk)

    doc = IAHashDocument(
        prompt_maestro=prompt_text,
        respuesta=respuesta_text,
        modelo=modelo,
        timestamp=timestamp,
        prompt_id=prompt_id,
        subject_id=subject_id,
        h_prompt=h_prompt,
        h_respuesta=h_respuesta,
        h_total=h_total,
        firma_total=firma_total,
        issuer_pk_url=issuer_pk_url,
        issuer_id=issuer_id,
    )
    return doc
