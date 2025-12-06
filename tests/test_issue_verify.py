from iahash.issuer import issue_document
from iahash.verifier import verify_document


def test_issue_and_verify_roundtrip(temp_keys):
    doc = issue_document(
        prompt_text="Hola IA",
        respuesta_text="Hola humano",
        modelo="gpt-test",
        prompt_id="demo",
        subject="tester",
        conversation_id="conv-1",
        timestamp="2024-01-01T00:00:00Z",
    )

    valid, reason = verify_document(doc)
    assert valid is True
    assert "valid" in reason
    assert doc.conversation_id == "conv-1"
