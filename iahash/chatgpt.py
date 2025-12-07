from __future__ import annotations

"""Utilities to read ChatGPT shared conversations."""

import json
import re
from dataclasses import dataclass
from typing import Any, Iterable

import httpx


class ChatGPTShareError(Exception):
    """Raised when a ChatGPT shared conversation cannot be parsed."""


@dataclass
class ChatGPTShare:
    prompt: str
    response: str
    model: str | None
    conversation_id: str | None


_NEXT_DATA_RE = re.compile(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)


def _extract_next_data(html: str) -> dict[str, Any]:
    match = _NEXT_DATA_RE.search(html)
    if not match:
        raise ChatGPTShareError("No se encontró la conversación compartida en la página.")

    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise ChatGPTShareError("No se pudo leer el JSON interno del share de ChatGPT.") from exc


def _find_conversation_candidates(data: dict[str, Any]) -> Iterable[dict[str, Any]]:
    props = data.get("props", {}) or {}
    page_props = props.get("pageProps", {}) or {}

    server_response = page_props.get("serverResponse", {}) or {}
    server_data = server_response.get("data", {}) or {}

    yield page_props.get("sharedConversation") or {}
    yield server_data.get("sharedConversation") or {}
    yield server_data.get("conversation") or {}
    yield server_data if isinstance(server_data, dict) else {}


def _extract_prompt_and_response(conversation: dict[str, Any]) -> tuple[str | None, str | None]:
    mapping = conversation.get("mapping") or {}
    messages = []
    for node in mapping.values():
        message = node.get("message") or {}
        role = (message.get("author") or {}).get("role")
        content = message.get("content") or {}
        parts = content.get("parts") or []
        text = "\n".join([part for part in parts if isinstance(part, str)]).strip()
        if not text or role not in {"user", "assistant"}:
            continue
        messages.append(
            {
                "role": role,
                "text": text,
                "created": message.get("create_time") or 0,
            }
        )

    messages.sort(key=lambda m: m["created"])

    prompt_text = next((m["text"] for m in messages if m["role"] == "user"), None)
    response_text = next((m["text"] for m in reversed(messages) if m["role"] == "assistant"), None)
    return prompt_text, response_text


def fetch_chatgpt_share(share_url: str, *, client: httpx.Client | None = None) -> ChatGPTShare:
    """Fetch and parse a ChatGPT shared conversation."""

    if not share_url.startswith("https://chatgpt.com/share/"):
        raise ChatGPTShareError("Sólo se aceptan URLs de https://chatgpt.com/share/…")

    owns_client = client is None
    if client is None:
        client = httpx.Client(timeout=10)

    try:
        res = client.get(share_url)
        res.raise_for_status()
    except httpx.HTTPError as exc:  # pragma: no cover - defensive
        if owns_client:
            client.close()
        raise ChatGPTShareError(f"Error al obtener el chat compartido: {exc}") from exc

    if owns_client:
        client.close()

    data = _extract_next_data(res.text)

    conversation: dict[str, Any] | None = None
    for candidate in _find_conversation_candidates(data):
        if candidate and isinstance(candidate, dict) and candidate.get("mapping"):
            conversation = candidate
            break

    if not conversation:
        raise ChatGPTShareError("No se encontró el contenido de la conversación compartida.")

    prompt_text, response_text = _extract_prompt_and_response(conversation)
    if not prompt_text or not response_text:
        raise ChatGPTShareError("No se pudieron extraer el prompt y la respuesta del share.")

    model = (
        conversation.get("model_slug")
        or conversation.get("model")
        or conversation.get("gptModel")
    )
    conversation_id = conversation.get("id") or conversation.get("conversation_id")

    return ChatGPTShare(
        prompt=prompt_text,
        response=response_text,
        model=model,
        conversation_id=str(conversation_id) if conversation_id else None,
    )

