"""Extractor for ChatGPT shared conversations.

This module downloads a ChatGPT shared conversation page, extracts the
embedded ``__NEXT_DATA__`` JSON payload, and reconstructs the original
user prompt and assistant response in the format expected by IA-HASH.

The parser aims to be resilient to layout changes in ChatGPT share pages by
searching for the conversation mapping dynamically instead of relying on
brittle, hard-coded paths.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterable, Optional
from urllib.parse import urlparse

import httpx

from iahash.extractors.exceptions import (
    InvalidShareURL,
    UnreachableSource,
    UnsupportedProvider,
)

# Accepted hostnames for ChatGPT share URLs.
CHATGPT_SHARE_HOSTS = {
    "chatgpt.com",
    "www.chatgpt.com",
    "chat.openai.com",
    "www.chat.openai.com",
}

# The shared conversation path prefix.
SHARE_PATH_PREFIX = "/share/"

ERROR_UNREACHABLE = "unreachable"
ERROR_PARSING = "parsing"
ERROR_UNSUPPORTED = "unsupported"

__all__ = [
    "extract_from_url",
    "extract_chatgpt_share",
    "extract_prompt_and_response_from_chatgpt_share",
    "extract_payload_from_chatgpt_share",
    "ERROR_UNREACHABLE",
    "ERROR_PARSING",
    "ERROR_UNSUPPORTED",
]


def _validate_share_url(url: str) -> None:
    """Validate that the URL points to a ChatGPT shared conversation.

    Args:
        url: The URL provided by the user.

    Raises:
        InvalidShareURL: if the URL does not match the expected host or path.
    """

    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"}:
        raise InvalidShareURL(
            "URL inválida. Debe usar http(s)://chatgpt.com/share/... o http(s)://chat.openai.com/share/..."
        )

    hostname = (parsed.hostname or "").lower()
    if hostname not in CHATGPT_SHARE_HOSTS:
        raise InvalidShareURL("URL inválida. Debe usar chatgpt.com o chat.openai.com")

    if not parsed.path.startswith(SHARE_PATH_PREFIX):
        raise InvalidShareURL("URL inválida. La ruta debe comenzar con /share/")

    # Require a non-empty identifier after /share/
    share_id = parsed.path[len(SHARE_PATH_PREFIX) :].strip("/")
    if not share_id:
        raise InvalidShareURL("URL inválida. Falta el identificador de la conversación compartida")


def _download_html(url: str, *, timeout: float = 10.0) -> str:
    """Download the share page HTML using a basic HTTP GET request."""

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
    }

    try:
        response = httpx.get(
            url,
            timeout=timeout,
            follow_redirects=True,
            headers=headers,
        )
    except httpx.HTTPError as exc:
        raise UnreachableSource(f"Connection error when fetching ChatGPT share URL: {exc}") from exc

    if response.status_code < 200 or response.status_code >= 300:
        raise UnreachableSource(f"HTTP {response.status_code} when fetching ChatGPT share URL")

    return response.text


def _extract_next_data(html: str) -> Dict[str, Any]:
    """Extract and parse the ``__NEXT_DATA__`` JSON payload from HTML.

    The ChatGPT share pages embed a ``<script id="__NEXT_DATA__">`` tag that
    contains the serialized data used by Next.js. We intentionally use a simple
    string/regex search to avoid depending on an HTML parser.

    Raises:
        UnsupportedProvider: if the tag is missing or the JSON cannot be parsed.
    """

    # Quick exit: if the entire HTML is already JSON (useful for tests).
    try:
        possible_json = json.loads(html)
        if isinstance(possible_json, dict):
            return possible_json
    except json.JSONDecodeError:
        pass

    match = re.search(
        r"<script[^>]+id=\"__NEXT_DATA__\"[^>]*>(.*?)</script>",
        html,
        re.DOTALL | re.IGNORECASE,
    )
    if not match:
        raise UnsupportedProvider("Could not find or parse __NEXT_DATA__ in ChatGPT share page")

    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise UnsupportedProvider("Could not find or parse __NEXT_DATA__ in ChatGPT share page") from exc


def _find_mapping(obj: Any) -> Optional[Dict[str, Any]]:
    """Recursively search for a conversation mapping structure.

    A valid mapping is a dictionary where the values are dictionaries that
    contain at least a ``"message"`` key. Only the first matching mapping is
    returned.
    """

    if isinstance(obj, dict):
        dict_values: Iterable[Any] = obj.values()
        candidate_values = [v for v in dict_values if isinstance(v, dict)]
        if candidate_values and any("message" in v for v in candidate_values):
            return obj
        for value in dict_values:
            found = _find_mapping(value)
            if found:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = _find_mapping(item)
            if found:
                return found
    return None


def _collect_messages(mapping: Dict[str, Any]) -> tuple[str, str]:
    """Collect the earliest user prompt and latest assistant response.

    The mapping is iterated in insertion order. When ``create_time`` is present,
    it is used to sort messages; otherwise iteration order is used as a fallback.

    Raises:
        UnsupportedProvider: if user or assistant messages cannot be found.
    """

    user_messages: list[tuple[tuple[int, float | int], str]] = []
    assistant_messages: list[tuple[tuple[int, float | int], str]] = []

    for idx, node in enumerate(mapping.values()):
        if not isinstance(node, dict):
            continue

        message = node.get("message") if isinstance(node, dict) else None
        if not isinstance(message, dict):
            continue

        role = (message.get("author") or {}).get("role")
        parts = message.get("content", {}).get("parts") or []
        text_parts = [part for part in parts if isinstance(part, str)]
        if not text_parts:
            continue

        text = "\n".join(text_parts)
        create_time = message.get("create_time")
        sort_key = (0, create_time) if isinstance(create_time, (int, float)) else (1, idx)

        if role == "user":
            user_messages.append((sort_key, text))
        elif role == "assistant":
            assistant_messages.append((sort_key, text))

    if not user_messages or not assistant_messages:
        raise UnsupportedProvider(
            "Could not parse ChatGPT shared conversation (missing user or assistant messages)"
        )

    prompt_text = min(user_messages, key=lambda item: item[0])[1]
    response_text = max(assistant_messages, key=lambda item: item[0])[1]
    return prompt_text, response_text


def _find_first_value(obj: Any, keys: set[str]) -> Optional[Any]:
    """Recursively search for the first value whose key matches ``keys``."""

    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in keys:
                return value
            found = _find_first_value(value, keys)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = _find_first_value(item, keys)
            if found is not None:
                return found
    return None


def _conversation_payload(next_data: Dict[str, Any]) -> Dict[str, str]:
    """Extract prompt, response, and model information from Next.js data."""

    mapping = _find_mapping(next_data)
    if not mapping:
        raise UnsupportedProvider("Could not find conversation mapping in ChatGPT share data")

    prompt_text, response_text = _collect_messages(mapping)

    model = _find_first_value(next_data, {"model", "modelSlug", "model_slug", "default_model_slug"})
    if not isinstance(model, str) or not model.strip():
        model = "unknown"

    return {
        "prompt_text": prompt_text,
        "response_text": response_text,
        "model": model,
    }


def extract_payload_from_chatgpt_share(data: Dict[str, Any]) -> Dict[str, str]:
    return _conversation_payload(data)


def extract_prompt_and_response_from_chatgpt_share(data: Dict[str, Any]) -> tuple[str, str]:
    payload = _conversation_payload(data)
    return payload["prompt_text"], payload["response_text"]


def _extract_payload(next_data: Dict[str, Any]) -> Dict[str, Any]:
    payload = extract_payload_from_chatgpt_share(next_data)
    payload["provider"] = "chatgpt"
    if "model" not in payload or not payload.get("model"):
        payload["model"] = payload.get("model") or "unknown"
    return payload


def extract_from_url(url: str) -> Dict[str, Any]:
    """Download and extract a ChatGPT shared conversation from a URL."""

    _validate_share_url(url)
    html = _download_html(url)

    next_data = _extract_next_data(html)

    payload = _extract_payload(next_data)
    payload["conversation_url"] = url
    payload["url"] = url
    return payload


def extract_chatgpt_share(url: str) -> Dict[str, Any]:
    """Compatibility alias for existing code."""

    return extract_from_url(url)
