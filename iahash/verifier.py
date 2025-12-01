from pathlib import Path

from .crypto import (
    normalise,
    sha256_hex,
    load_public_key,
    verify_signature_hex,
)
from .models import IAHashDocument

KEYS_DIR = Path("keys")
PK_PATH = KEYS_DIR / "iah_pk.pem"


def verify_document(doc: IAHashDocument) -> tuple[bool, str]:
    """
    Verify integrity and authenticity of an IA-HASH document.
    Returns (valid: bool, reason: str).
    """

    # 1) Recalculate hashes from raw text
    h_prompt_local = sha256_hex(normalise(doc.prompt_maestro))
    if h_prompt_local != doc.h_prompt:
        return False, "Prompt Maestro has been modified"

    h_respuesta_local = sha256_hex(normalise(doc.respuesta))
    if h_respuesta_local != doc.h_respuesta:
        return False, "Response has been modified"

    # 2) Recalculate combined hash
    cadena_total = "|".join(
        [
            doc.version,
            doc.prompt_id or "",
            doc.h_prompt,
            doc.h_respuesta,
            doc.modelo,
            doc.timestamp,
        ]
    )
    h_total_local = sha256_hex(cadena_total.encode("utf-8"))
    if h_total_local != doc.h_total:
        return False, "Metadata has been modified"

    # 3) Verify signature
    pk = load_public_key(PK_PATH)
    if not verify_signature_hex(doc.h_total, doc.firma_total, pk):
        return False, "Invalid signature (not issued by declared issuer)"

    return True, "IA-HASH document is valid and unmodified"
