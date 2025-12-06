from iahash.issuer import issue_document
from iahash.verifier import verify_document


def test_verifier_accepts_valid_document(temp_keys):
    doc = issue_document(
        prompt_text="Pregunta?",
        respuesta_text="Respuesta",
        modelo="gpt-x",
    )
    valid, reason = verify_document(doc)
    assert valid is True
    assert "valid" in reason.lower()


def test_verifier_rejects_tampered_fields(temp_keys):
    doc = issue_document(
        prompt_text="Original",
        respuesta_text="Contenido",
        modelo="gpt-x",
    )

    tampered_prompt = doc.model_copy(update={"prompt_maestro": "Original modificado"})
    valid_prompt, reason_prompt = verify_document(tampered_prompt)
    assert valid_prompt is False
    assert "prompt" in reason_prompt.lower()

    tampered_response = doc.model_copy(update={"respuesta": "Otro"})
    valid_resp, reason_resp = verify_document(tampered_response)
    assert valid_resp is False
    assert "response" in reason_resp.lower()

    tampered_meta = doc.model_copy(update={"modelo": "otro-modelo"})
    valid_meta, reason_meta = verify_document(tampered_meta)
    assert valid_meta is False
    assert "context" in reason_meta.lower()
