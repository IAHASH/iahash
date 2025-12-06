"""Master prompt loading and hashing utilities.

This module centralises how IA-HASH master prompts are discovered and
hashed. It reads the canonical prompt catalogue from ``docs/prompts`` and
optionally merges any runtime additions stored under ``db``.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Iterable, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .crypto import normalise, sha256_hex

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_PROMPTS_PATH = BASE_DIR / "docs" / "prompts" / "master_prompts.json"
CUSTOM_PROMPTS_PATH = BASE_DIR / "db" / "master_prompts.custom.json"


class MasterPrompt(BaseModel):
    """Master prompt definition with deterministic hash."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Stable identifier (PROMPT-ID)")
    title: str
    version: str
    language: str = Field(default="es")
    category: Optional[str] = None
    description: Optional[str] = None
    body: str = Field(..., description="Full prompt text")
    metadata: dict = Field(default_factory=dict)
    prompt_hash: str = Field(..., description="SHA256 over the normalised body")

    @field_validator("prompt_hash")
    @classmethod
    def validate_prompt_hash(cls, value: str, info):  # type: ignore[override]
        body = info.data.get("body")
        if body is None:
            return value
        expected = sha256_hex(normalise(body))
        if value != expected:
            raise ValueError("prompt_hash does not match body")
        return value

    @classmethod
    def from_raw(cls, data: dict) -> "MasterPrompt":
        body = data.get("body", "")
        prompt_hash = data.get("prompt_hash") or sha256_hex(normalise(body))
        return cls(**{**data, "prompt_hash": prompt_hash})

    def summary(self) -> "MasterPromptSummary":
        return MasterPromptSummary(
            id=self.id,
            title=self.title,
            version=self.version,
            language=self.language,
            category=self.category,
            description=self.description,
            prompt_hash=self.prompt_hash,
        )


class MasterPromptSummary(BaseModel):
    """Public metadata for listings without the full body."""

    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    version: str
    language: str
    category: Optional[str] = None
    description: Optional[str] = None
    prompt_hash: str


def _load_records(path: Path) -> Iterable[dict]:
    if not path.exists():
        return []
    raw = json.loads(path.read_text())
    if not isinstance(raw, list):
        return []
    return raw


def _merge_catalogues() -> List[MasterPrompt]:
    base_records = list(_load_records(DEFAULT_PROMPTS_PATH))
    custom_records = list(_load_records(CUSTOM_PROMPTS_PATH))
    merged: dict[str, MasterPrompt] = {}
    for record in base_records + custom_records:
        prompt = MasterPrompt.from_raw(record)
        merged[prompt.id] = prompt
    return list(merged.values())


@lru_cache(maxsize=1)
def list_master_prompts() -> List[MasterPromptSummary]:
    """Return all master prompts with hashes but without bodies."""

    return [prompt.summary() for prompt in _merge_catalogues()]


@lru_cache(maxsize=1)
def list_master_prompts_full() -> List[MasterPrompt]:
    return _merge_catalogues()


def get_master_prompt(prompt_id: str) -> Optional[MasterPrompt]:
    for prompt in list_master_prompts_full():
        if prompt.id == prompt_id:
            return prompt
    return None


def save_custom_prompt(data: dict) -> MasterPrompt:
    """Append or replace a custom prompt in the runtime catalogue."""

    CUSTOM_PROMPTS_PATH.parent.mkdir(exist_ok=True)
    current = list(_load_records(CUSTOM_PROMPTS_PATH))
    prompt = MasterPrompt.from_raw(data)

    updated = [item for item in current if item.get("id") != prompt.id]
    updated.append(prompt.model_dump())
    CUSTOM_PROMPTS_PATH.write_text(json.dumps(updated, indent=2, ensure_ascii=False))

    list_master_prompts.cache_clear()
    list_master_prompts_full.cache_clear()
    return prompt
