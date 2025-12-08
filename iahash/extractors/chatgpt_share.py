"""Extractor for ChatGPT shared conversations using the backend API.

This module starts from a public URL like:

    https://chatgpt.com/share/XXXXXXXXXXXX
    https://chat.openai.com/share/XXXXXXXXXXXX

and internally calls:

    https://<host>/backend-api/share/XXXXXXXXXXXX

The backend API returns JSON describing the shared conversation.
From that payload we reconstruct:

- the original user prompt (first message with role == "user")
- the main assistant response (last message with role == "assistant")
- the model used (when available)

The result is returned in the format expected by IA-HASH
for type="CONVERSATION" documents.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional
from urllib.parse import urlparse, urlunparse

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

# Shared conversation path prefix.
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


# ---------------------------------------------------------------------------
# 1. URL validation and backend-api URL construction
# ---------------------------------------------------------------------------


def _validate_share_url(url: str) -> None:
    """Validate that the URL points to a ChatGPT shared conversation."""
    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"}:
        raise InvalidShareURL(
            "URL inválida. Debe usar http(s)://chatgpt.com/share/... "
            "o http(s)://chat.openai.com/share/..."
        )

    hostname = (parsed.hostname or "").lower()
    if hostname not in CHATGPT_SHARE_HOSTS:
        raise InvalidShareURL(
            "URL inválida. Debe usar chatgpt.com o chat.openai.com"
        )

    if not parsed.path.startswith(SHARE_PATH_PREFIX):
        raise InvalidShareURL("URL inválida. La ruta debe comenzar con /share/")

    # Require a non-empty identifier after /share/
    share_id = parsed.path[len(SHARE_PATH_PREFIX):].strip("/")
    if not share_id:
        raise InvalidShareURL(
            "URL inválida. Falta el identificador de la conversación compartida"
        )


def _backend_api_url_from_share(url: str) -> str:
    """Convert:

        https://chatgpt.com/share/ID
        https://chat.openai.com/share/ID

    into:

        https://<host>/backend-api/share/ID
    """
    parsed = urlparse(url)

    if not parsed.path.startswith(SHARE_PATH_PREFIX):
        raise InvalidShareURL("URL inválida. La ruta debe comenzar con /share/")

    share_id = parsed.path[len(SHARE_PATH_PREFIX):].strip("/")
    backend_path = f"/backend-api/share/{share_id}"

    backend_parsed = parsed._replace(
        path=backend_path,
        query="",      # clean query just in case
        fragment="",   # and fragment too
    )

    return urlunparse(backend_parsed)


# ---------------------------------------------------------------------------
# 2. Download JSON from backend-api/share
# ---------------------------------------------------------------------------


def _download_share_payload(url: str, *, timeout: float = 10.0) -> Dict[str, Any]:
    """Download JSON from ChatGPT backend-api/share."""
    backend_url = _backend_api_url_from_share(url)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain;q=0.9,*/*;q=0.8",
    }

    try:
        response = httpx.get(
            backend_url,
            timeout=timeout,
            follow_redirects=True,
            headers=headers,
        )
    except httpx.HTTPError as exc:
        raise UnreachableSource(
            f"Connection error when fetching ChatGPT share backend URL: {exc}"
        ) from exc

    if not (200 <= response.status_code < 300):
        raise UnreachableSource(
            f"HTTP {response.status_code} when fetching ChatGPT share backend URL"
        )

    try:
        return response.json()
    except ValueError as exc:
        # We expected JSON from backend-api/share
        raise UnsupportedProvider(
            "Expected JSON from ChatGPT backend-api/share endpoint"
        ) from exc


# ---------------------------------------------------------------------------
# 3. Generic search helpers on the backend payload
# ---------------------------------------------------------------------------


def _find_mapping(obj: Any) -> Optional[Dict[str, Any]]:
    """Recursively search for a conversation mapping structure.

    We consider 'mapping' any dict whose values (also dicts) contain
    at least a "message" key.
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
    """Return (prompt_text, response_text) from the mapping.

    - Prompt: earliest message with role == "user"
    - Response: latest message with role == "assistant"

    If `create_time` exists, it is used for ordering; otherwise
    we fall back to iteration order.
    """
    user_messages: list[tuple[tuple[int, float | int], str]] = []
    assistant_messages: list[tuple[tuple[int, float | int], str]] = []

    for idx, node in enumerate(mapping.values()):
        if not isinstance(node, dict):
            continue

        message = node.get("message")
        if not isinstance(message, dict):
            continue

        author = message.get("author") or {}
        role = author.get("role")

        content = message.get("content") or {}
        parts = content.get("parts") or []
        text_parts = [part for part in parts if isinstance(part, str)]

        if not text_parts:
            continue

        text = "\n".join(text_parts)
        create_time = message.get("create_time")

        # (0, t) when there is a numeric timestamp, (1, idx) as fallback
        sort_key: tuple[int, float | int] = (
            (0, create_time)
            if isinstance(create_time, (int, float))
            else (1, idx)
        )

        if role == "user":
            user_messages.append((sort_key, text))
        elif role == "assistant":
            assistant_messages.append((sort_key, text))

    if not user_messages or not assistant_messages:
        raise UnsupportedProvider(
            "Could not parse ChatGPT shared conversation "
            "(missing user or assistant messages)"
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


def _conversation_payload(backend_data: Dict[str, Any]) -> Dict[str, str]:
    """Extract prompt, response and model information from backend-api data."""
    mapping = _find_mapping(backend_data)
    if not mapping:
        raise UnsupportedProvider(
            "Could not find conversation mapping in ChatGPT share backend data"
        )

    prompt_text, response_text = _collect_messages(mapping)

    model = _find_first_value(
        backend_data,
        {"model", "modelSlug", "model_slug", "default_model_slug"},
    )

    if not isinstance(model, str) or not model.strip():
        model = "unknown"

    return {
        "prompt_text": prompt_text,
        "response_text": response_text,
        "model": model,
    }


# ---------------------------------------------------------------------------
# 4. Public extractor API
# ---------------------------------------------------------------------------


def extract_payload_from_chatgpt_share(data: Dict[str, Any]) -> Dict[str, str]:
    """Return a dict with `prompt_text`, `response_text` and `model`."""
    return _conversation_payload(data)


def extract_prompt_and_response_from_chatgpt_share(
    data: Dict[str, Any],
) -> tuple[str, str]:
    """Return only (prompt_text, response_text)."""
    payload = _conversation_payload(data)
    return payload["prompt_text"], payload["response_text"]


def _extract_payload(backend_data: Dict[str, Any]) -> Dict[str, Any]:
    """Enrich payload with IA-HASH specific metadata."""
    payload = extract_payload_from_chatgpt_share(backend_data)
    payload["provider"] = "chatgpt"

    if not payload.get("model"):
        payload["model"] = "unknown"

    return payload


def extract_from_url(url: str) -> Dict[str, Any]:
    """Download and extract a ChatGPT shared conversation from a URL."""
    _validate_share_url(url)
    backend_data = _download_share_payload(url)
    payload = _extract_payload(backend_data)
    payload["conversation_url"] = url
    payload["url"] = url
    return payload


def extract_chatgpt_share(url: str) -> Dict[str, Any]:
    """Compatibility alias for existing code."""
    return extract_from_url(url)
