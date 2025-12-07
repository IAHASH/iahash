import pytest

pytest.skip(
    "Legacy issuer tests are skipped because issue_document is not available in this build.",
    allow_module_level=True,
)

from iahash.crypto import normalise, sha256_hex
from iahash.issuer import issue_document


def test_issue_document_hashes_and_signature(temp_keys):
    doc = issue_document(
        prompt_text="Hola IA",
        respuesta_text="Respuesta demo",
        modelo="demo-model",
        prompt_id="PROMPT-1",
        subject="user-1",
    )

    assert len(doc.h_prompt) == 64
    assert len(doc.h_respuesta) == 64
    assert len(doc.h_total) == 64
    assert doc.modelo == "demo-model"

    expected_h_prompt = sha256_hex(normalise("Hola IA"))
    expected_h_respuesta = sha256_hex(normalise("Respuesta demo"))
    expected_total = sha256_hex(
        "|".join([doc.version, expected_h_prompt, expected_h_respuesta, doc.h_contexto]).encode("utf-8")
    )

    assert doc.h_prompt == expected_h_prompt
    assert doc.h_respuesta == expected_h_respuesta
    assert doc.h_total == expected_total
    assert len(doc.h_contexto) == 64
