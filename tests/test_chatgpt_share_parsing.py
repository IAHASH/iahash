import json
from pathlib import Path

import pytest

from iahash.extractors.chatgpt_share import (
    _collect_messages,
    _extract_next_data,
    _find_mapping,
    extract_payload_from_chatgpt_share,
)
from iahash.extractors.exceptions import UnsupportedProvider


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "chatgpt_share_sample.html"


def load_fixture() -> str:
    return FIXTURE_PATH.read_text(encoding="utf-8")


def test_extract_next_data_parses_fixture():
    html = load_fixture()
    data = _extract_next_data(html)

    assert isinstance(data, dict)
    assert "props" in data


def test_extract_next_data_without_script_tag_raises():
    with pytest.raises(UnsupportedProvider):
        _extract_next_data("<html><body>No data</body></html>")


def test_find_mapping_recurses_into_nested_structures():
    nested = {"outer": [{"inner": {"node": {"message": {"author": {"role": "user"}}}}}]}
    mapping = _find_mapping(nested)

    assert mapping == {"node": {"message": {"author": {"role": "user"}}}}


def test_collect_messages_uses_time_and_ordering():
    mapping = {
        "u2": {
            "message": {
                "author": {"role": "user"},
                "content": {"parts": ["Later user"]},
                "create_time": 2,
            }
        },
        "u1": {
            "message": {
                "author": {"role": "user"},
                "content": {"parts": ["First user"]},
                "create_time": 1,
            }
        },
        "a1": {
            "message": {
                "author": {"role": "assistant"},
                "content": {"parts": ["First assistant"]},
                "create_time": 3,
            }
        },
        "a2": {
            "message": {
                "author": {"role": "assistant"},
                "content": {"parts": ["Latest assistant"]},
                "create_time": 4,
            }
        },
    }

    prompt_text, response_text = _collect_messages(mapping)

    assert prompt_text == "First user"
    assert response_text == "Latest assistant"


def test_collect_messages_requires_user_and_assistant():
    mapping = {
        "only_user": {
            "message": {
                "author": {"role": "user"},
                "content": {"parts": ["Hello"]},
            }
        }
    }

    with pytest.raises(UnsupportedProvider):
        _collect_messages(mapping)


def test_extract_payload_from_chatgpt_share_returns_texts():
    html = load_fixture()
    next_data = _extract_next_data(html)

    payload = extract_payload_from_chatgpt_share(next_data)

    assert payload["prompt_text"] == "Hola, ¿puedes resumir mi perfil?"
    assert payload["response_text"] == "Aquí tienes un resumen de tu perfil profesional."
    assert payload["model"] == "gpt-4o"
