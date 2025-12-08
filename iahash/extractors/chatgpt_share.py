"""Extractor for ChatGPT shared conversations using backend API + HTML fallback.

Starting from a public URL like:

    https://chatgpt.com/share/XXXXXXXXXXXX
    https://chat.openai.com/share/XXXXXXXXXXXX

we try first:

    https://<host>/backend-api/share/XXXXXXXXXXXX   (JSON)

If that fails (e.g. HTTP 4xx/5xx from backend), we fall back to:

    https://<host>/share/XXXXXXXXXXXX               (HTML + __NEXT_DATA__)

From the resulting JSON payload we reconstruct:

- the original user prompt (FIRST real instruction)
- the assistant response (FIRST answer to that instruction)
- the model used (when available)

Returned in the format expected by IA-HASH for type="CONVERSATION" documents.
"""

from __future__ import annotations

import json
import re
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
# 1. URL validation and helpers
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

    share_id = parsed.path[len(SHARE_PATH_PREFIX) :].strip("/")
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

    share_id = parsed.path[len(SHARE_PATH_PREFIX) :].strip("/")
    backend_path = f"/backend-api/share/{share_id}"

    backend_parsed = parsed._replace(
        path=backend_path,
        query="",   # clean query
        fragment="",  # and fragment
    )

    return urlunparse(backend_parsed)


# ---------------------------------------------------------------------------
# 2. Download helpers: backend JSON + HTML fallback
# ---------------------------------------------------------------------------


def _download_html(url: str, *, timeout: float = 10.0) -> str:
    """Download the HTML share page."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
    }

    try:
        response = httpx.get(
            url,
            timeout=timeout,
            follow_redirects=True,
            headers=headers,
        )
    except httpx.HTTPError as exc:
        raise UnreachableSource(
            f"Connection error when fetching ChatGPT share HTML: {exc}"
        ) from exc

    if not (200 <= response.status_code < 300):
        raise UnreachableSource(
            f"HTTP {response.status_code} when fetching ChatGPT share HTML"
        )

    return response.text


def _extract_next_data(html: str) -> Dict[str, Any]:
    """Extract and parse the JSON from __NEXT_DATA__ inside the HTML page."""
    main_pattern = re.compile(
        r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(?P<json>{.*?})</script>',
        re.DOTALL | re.IGNORECASE,
    )

    match = main_pattern.search(html)

    if not match:
        fallback_pattern = re.compile(
            r'__NEXT_DATA__[^>]*>\s*(?P<json>{.*?})\s*</script>',
            re.DOTALL | re.IGNORECASE,
        )
        match = fallback_pattern.search(html)

    if not match:
        raise UnsupportedProvider(
            "Could not find or parse __NEXT_DATA__ in ChatGPT share page"
        )

    raw_json = match.group("json")

    try:
        return json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise UnsupportedProvider(
            "Could not find or parse __NEXT_DATA__ in ChatGPT share page"
        ) from exc


def _download_share_payload(url: str, *, timeout: float = 10.0) -> Dict[str, Any]:
    """Download JSON for the shared conversation.

    Strategy:
    1) Try backend-api/share (JSON).
    2) If that fails (HTTP error, 4xx/5xx, non-JSON...), fall back to:
       - HTML share page + __NEXT_DATA__.
    """
    backend_url = _backend_api_url_from_share(url)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain;q=0.9,*/*;q=0.8",
    }

    backend_error: Optional[Exception] = None

    # 1) Try backend-api/share
    try:
        response = httpx.get(
            backend_url,
            timeout=timeout,
            follow_redirects=True,
            headers=headers,
        )
        if 200 <= response.status_code < 300:
            try:
                return response.json()
            except ValueError as exc:
                backend_error = exc
        else:
            backend_error = RuntimeError(
                f"HTTP {response.status_code} from backend-api/share"
            )
    except httpx.HTTPError as exc:
        backend_error = exc

    # 2) Fallback: HTML + __NEXT_DATA__
    try:
        html = _download_html(url, timeout=timeout)
        next_data = _extract_next_data(html)
        return next_data
    except UnreachableSource as exc:
        detail = f"Cannot fetch ChatGPT share URL via backend-api or HTML: {exc}"
        if backend_error is not None:
            detail += f" (backend error: {backend_error})"
        raise UnreachableSource(detail) from exc
    except UnsupportedProvider as exc:
        detail = (
            "Could not parse ChatGPT share page via backend-api or HTML "
            f"(backend error: {backend_error})"
        )
        raise UnsupportedProvider(detail) from exc


# ---------------------------------------------------------------------------
# 3. Generic search helpers on the payload
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


def _collect_first_pair(mapping: Dict[str, Any]) -> tuple[str, str, Dict[str, Any]]:
    """Return (prompt_text, response_text, assistant_message_metadata).

    Rules:

    - Prompt:
      * first message with role == "user"
      * content_type == "text"
      * NOT metadata.is_user_system_message
      * NOT metadata.is_visually_hidden_from_conversation
      * with non-empty text.

    - Response:
      * first message with role == "assistant"
      * content_type == "text"
      * comes AFTER the chosen prompt in time/order
      * if possible, prefer metadata.channel == "final".

    This guarantees we sign the FIRST real instruction and its FIRST answer,
    even if the user later adds more instructions or refinements.
    """
    user_msgs: list[tuple[tuple[int, float | int], str]] = []
    assistant_msgs: list[tuple[tuple[int, float | int], str, Dict[str, Any]]] = []

    for idx, node in enumerate(mapping.values()):
        if not isinstance(node, dict):
            continue

        message = node.get("message")
        if not isinstance(message, dict):
            continue

        author = message.get("author") or {}
        role = author.get("role")

        content = message.get("content") or {}
        content_type = content.get("content_type")
        parts = content.get("parts") or []

        # Only text messages matter.
        if content_type != "text":
            continue

        text_parts = [part for part in parts if isinstance(part, str)]
        if not text_parts:
            continue

        text = "\n".join(text_parts)
        metadata: Dict[str, Any] = message.get("metadata") or {}

        create_time = message.get("create_time")
        sort_key: tuple[int, float | int] = (
            (0, create_time)
            if isinstance(create_time, (int, float))
            else (1, idx)
        )

        if role == "user":
            if metadata.get("is_user_system_message"):
                continue
            if metadata.get("is_visually_hidden_from_conversation"):
                continue
            user_msgs.append((sort_key, text))

        elif role == "assistant":
            assistant_msgs.append((sort_key, text, metadata))

    if not user_msgs or not assistant_msgs:
        raise UnsupportedProvider(
            "Could not parse ChatGPT shared conversation "
            "(missing user or assistant messages)"
        )

    # First real prompt
    prompt_sort_key, prompt_text = min(user_msgs, key=lambda item: item[0])

    # Assistants that come AFTER that prompt.
    candidates = [
        (skey, text, meta)
        for (skey, text, meta) in assistant_msgs
        if skey >= prompt_sort_key
    ]

    if not candidates:
        raise UnsupportedProvider(
            "Could not find assistant response after first user prompt"
        )

    # Prefer channel == "final" if present.
    final_candidates = [
        item for item in candidates if (item[2].get("channel") == "final")
    ]
    pool = final_candidates or candidates

    _, response_text, response_metadata = min(pool, key=lambda item: item[0])
    return prompt_text, response_text, response_metadata


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


def _conversation_payload(data: Dict[str, Any]) -> Dict[str, str]:
    """Extract prompt, response and model information from payload data,
    always using the FIRST real prompt and its FIRST assistant answer.
    """
    mapping = _find_mapping(data)
    if not mapping:
        raise UnsupportedProvider(
            "Could not find conversation mapping in ChatGPT share data"
        )

    prompt_text, response_text, response_meta = _collect_first_pair(mapping)

    # Model: try the one from the assistant message first.
    model = (
        response_meta.get("model_slug")
        or response_meta.get("model")
        or _find_first_value(
            data,
            {"model", "modelSlug", "model_slug", "default_model_slug"},
        )
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


def _extract_payload(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """Enrich payload with IA-HASH specific metadata."""
    payload = extract_payload_from_chatgpt_share(raw_data)
    payload["provider"] = "chatgpt"

    if not payload.get("model"):
        payload["model"] = "unknown"

    return payload


def extract_from_url(url: str) -> Dict[str, Any]:
    """Download and extract a ChatGPT shared conversation from a URL."""
    _validate_share_url(url)
    raw_data = _download_share_payload(url)
    payload = _extract_payload(raw_data)
    payload["conversation_url"] = url
    payload["url"] = url
    return payload


def extract_chatgpt_share(url: str) -> Dict[str, Any]:
    """Compatibility alias for existing code."""
    return extract_from_url(url)