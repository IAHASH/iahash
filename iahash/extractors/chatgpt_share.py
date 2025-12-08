"""Extractor for ChatGPT shared conversations."""

from __future__ import annotations

import json
import re
from typing import Dict, Optional
from urllib.parse import urlparse

import httpx

from iahash.extractors.exceptions import UnreachableSource, UnsupportedProvider

CHATGPT_SHARE_HOSTS = {"chat.openai.com", "chatgpt.com"}
SHARE_PATH_FRAGMENT = "/share/"
SHARE_UUID_PATTERN = re.compile(
    r"^/share/(?P<uuid>[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})(?:/)?$"
)

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
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise UnsupportedProvider(
            "URL inválida. Debe usar https://chatgpt.com/share/... o https://chat.openai.com/share/..."
        )

    hostname = (parsed.hostname or "").lower()
    if hostname not in CHATGPT_SHARE_HOSTS:
        raise UnsupportedProvider(
            "URL inválida. Debe usar chatgpt.com o chat.openai.com"
        )

    if not parsed.path.startswith(SHARE_PATH_FRAGMENT):
        raise UnsupportedProvider(
            "URL inválida. La ruta debe comenzar con /share/"
        )

    if not SHARE_UUID_PATTERN.match(parsed.path):
        raise UnsupportedProvider("Unsupported conversation format")


def _download_html(url: str, *, timeout: float = 15.0) -> str:
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
        response.raise_for_status()
        return response.text
    except httpx.HTTPStatusError as exc:  # pragma: no cover - defensive branch
        status = exc.response.status_code if exc.response else "unknown"
        raise UnreachableSource(
            f"HTTP {status} when fetching ChatGPT share URL"
        ) from exc
    except httpx.HTTPError as exc:  # pragma: no cover - defensive branch
        raise UnreachableSource(
            f"Connection error when fetching ChatGPT share URL: {exc}"
        ) from exc


def _parse_next_data(html: str) -> Optional[Dict]:
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
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def _collect_messages(mapping: Dict) -> tuple[Optional[str], Optional[str]]:
    users: list[str] = []
    assistants: list[str] = []
    for node in mapping.values():
        message = node.get("message") if isinstance(node, dict) else None
        if not message:
            continue
        author_role = (message.get("author") or {}).get("role")
        parts = message.get("content", {}).get("parts") or []
        text = "\n".join(part for part in parts if isinstance(part, str))
        if author_role == "user":
            users.append(text)
        elif author_role == "assistant":
            assistants.append(text)
    prompt_text = users[0] if users else None
    response_text = assistants[-1] if assistants else None
    return prompt_text, response_text


def _conversation_payload(data: Dict) -> Dict[str, str]:
    try:
        page_props = data.get("props", {}).get("pageProps", {}) if isinstance(data, dict) else {}
        conversation = (
            page_props.get("sharedConversation")
            or page_props.get("serverResponse", {}).get("data", {})
            or data.get("sharedConversation")
            or data.get("serverResponse", {}).get("data", {})
        )
    except Exception as exc:  # pragma: no cover - defensive branch
        raise UnsupportedProvider(
            "Could not parse ChatGPT shared conversation (missing expected fields)"
        ) from exc

    if not conversation:
        raise UnsupportedProvider(
            "Could not parse ChatGPT shared conversation (missing expected fields)"
        )

    mapping = conversation.get("mapping") or {}
    prompt_text, response_text = _collect_messages(mapping)
    if not prompt_text or not response_text:
        raise UnsupportedProvider(
            "Could not parse ChatGPT shared conversation (missing expected fields)"
        )

    model = conversation.get("modelSlug") or conversation.get("model") or "unknown"
    return {
        "prompt_text": prompt_text,
        "response_text": response_text,
        "model": model,
    }


def extract_payload_from_chatgpt_share(data: Dict) -> Dict[str, str]:
    return _conversation_payload(data)


def extract_prompt_and_response_from_chatgpt_share(data: Dict) -> tuple[str, str]:
    payload = _conversation_payload(data)
    return payload["prompt_text"], payload["response_text"]


def _extract_payload(next_data: Dict) -> Dict[str, str]:
    payload = extract_payload_from_chatgpt_share(next_data)
    payload["provider"] = "chatgpt"
    if "model" not in payload:
        payload["model"] = payload.get("model") or "unknown"
    return payload


def extract_from_url(url: str) -> Dict[str, str]:
    """Descarga y extrae una conversación compartida de ChatGPT.

    Args:
        url: Enlace público generado por ChatGPT para compartir una conversación.

    Raises:
        UnsupportedProvider: si la URL no coincide con ChatGPT share o el formato es desconocido.
        UnreachableSource: si ocurre un error al descargar el HTML.

    Returns:
        Diccionario con prompt, respuesta, modelo y proveedor.
    """

    _validate_share_url(url)
    html = _download_html(url)

    next_data = _parse_next_data(html)
    if not next_data:
        raise UnsupportedProvider(
            "Could not parse ChatGPT shared conversation (missing expected fields)"
        )

    payload = _extract_payload(next_data)
    payload["conversation_url"] = url
    return payload


def extract_chatgpt_share(url: str) -> Dict[str, str]:
    """Alias de compatibilidad para código existente."""

    return extract_from_url(url)

