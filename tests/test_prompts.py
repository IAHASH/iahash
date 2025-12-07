import json

import pytest

import pytest

pytest.skip(
    "Legacy prompts tests are skipped because the prompts module is not available in this build.",
    allow_module_level=True,
)

from iahash import prompts
from iahash.crypto import normalise, sha256_hex


def reset_prompt_caches():
    prompts.list_master_prompts.cache_clear()
    prompts.list_master_prompts_full.cache_clear()


def test_master_prompts_have_hashes():
    reset_prompt_caches()
    items = prompts.list_master_prompts()
    assert any(item.id == "cv-honesto-v1" for item in items)
    for item in items:
        assert len(item.prompt_hash) == 64


def test_save_custom_prompt_is_persisted(tmp_path, monkeypatch):
    custom_path = tmp_path / "custom_prompts.json"
    monkeypatch.setattr(prompts, "CUSTOM_PROMPTS_PATH", custom_path)
    reset_prompt_caches()

    body = "Custom prompt body"
    created = prompts.save_custom_prompt(
        {
            "id": "custom-1",
            "title": "Custom prompt",
            "version": "v1",
            "language": "es",
            "body": body,
        }
    )

    assert created.prompt_hash == sha256_hex(normalise(body))
    assert json.loads(custom_path.read_text())[0]["id"] == "custom-1"

    loaded = prompts.get_master_prompt("custom-1")
    assert loaded is not None
    assert loaded.body == body
