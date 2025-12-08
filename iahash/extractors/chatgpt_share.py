"""Extractor para conversaciones compartidas de ChatGPT.

Este módulo parte de una URL pública tipo:

    https://chatgpt.com/share/XXXXXXXXXXXX

y la convierte internamente en una llamada a:

    https://chatgpt.com/backend-api/share/XXXXXXXXXXXX

De esa llamada obtenemos un JSON con la conversación compartida y
reconstruimos:

- el prompt de usuario "original" (primer mensaje con role == "user")
- la respuesta "principal" (último mensaje con role == "assistant")
- el modelo utilizado (si está disponible)

Devolvemos estos datos en el formato que espera IA-HASH para generar
un documento type="CONVERSATION".
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

# Dominios aceptados para URLs compartidas de ChatGPT.
CHATGPT_SHARE_HOSTS = {
    "chatgpt.com",
    "www.chatgpt.com",
    "chat.openai.com",
    "www.chat.openai.com",
}

# Prefijo de la ruta de conversaciones públicas.
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
# 1. Validación de URL y construcción de backend-api URL
# ---------------------------------------------------------------------------


def _validate_share_url(url: str) -> None:
    """Valida que la URL apunte a una conversación compartida de ChatGPT."""
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

    # Debe haber un identificador después de /share/
    share_id = parsed.path[len(SHARE_PATH_PREFIX) :].strip("/")
    if not share_id:
        raise InvalidShareURL(
            "URL inválida. Falta el identificador de la conversación compartida"
        )


def _backend_api_url_from_share(url: str) -> str:
    """Convierte:

        https://chatgpt.com/share/ID

    en:

        https://chatgpt.com/backend-api/share/ID
    """
    parsed = urlparse(url)

    # Forzamos el path a /backend-api/share/<id>
    if not parsed.path.startswith(SHARE_PATH_PREFIX):
        raise InvalidShareURL("URL inválida. La ruta debe comenzar con /share/")

    share_id = parsed.path[len(SHARE_PATH_PREFIX) :].strip("/")
    backend_path = f"/backend-api/share/{share_id}"

    backend_parsed = parsed._replace(
        path=backend_path,
        query="",      # limpiamos query por si acaso
        fragment="",   # y fragmento
    )

    return urlunparse(backend_parsed)


# ---------------------------------------------------------------------------
# 2. Descarga del JSON de backend-api/share
# ---------------------------------------------------------------------------


def _download_share_payload(url: str, *, timeout: float = 10.0) -> Dict[str, Any]:
    """Descarga el JSON de la API interna de share de ChatGPT."""
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
        # Esperábamos JSON del backend-api
        raise UnsupportedProvider(
            "Expected JSON from ChatGPT backend-api/share endpoint"
        ) from exc


# ---------------------------------------------------------------------------
# 3. Búsqueda genérica dentro del payload
# ---------------------------------------------------------------------------


def _find_mapping(obj: Any) -> Optional[Dict[str, Any]]:
    """Busca recursivamente un diccionario que se comporte como el 'mapping'
    de conversación de ChatGPT.

    Consideramos 'mapping' cualquier dict cuyos valores (también dict) contengan
    al menos una clave "message".
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
    """Devuelve (prompt_text, response_text) a partir del mapping.

    - Prompt: primer mensaje de role == "user"
    - Respuesta: último mensaje de role == "assistant"

    Si existe `create_time`, se usa para ordenar; si no, se usa el orden
    de iteración como fallback.
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

        # (0, t) si hay timestamp numérico, (1, idx) como fallback
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
    """Busca recursivamente el primer valor cuyo nombre de clave esté en keys."""
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
    """Construye el payload de conversación a partir del JSON devuelto por
    backend-api/share.
    """
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
# 4. API interna del extractor
# ---------------------------------------------------------------------------


def extract_payload_from_chatgpt_share(data: Dict[str, Any]) -> Dict[str, str]:
    """Devuelve un dict con `prompt_text`, `response_text` y `model`."""
    return _conversation_payload(data)


def extract_prompt_and_response_from_chatgpt_share(
    data: Dict[str, Any],
) -> tuple[str, str]:
    """Devuelve sólo (prompt_text, response_text)."""
    payload = _conversation_payload(data)
    return payload["prompt_text"], payload["response_text"]


def _extract_payload(backend_data: Dict[str, Any]) -> Dict[str, Any]:
    """Enriquece el payload con metadatos específicos de IA-HASH."""
    payload: Dict[str, Any] = extract_payload_from_chatgpt_share(backend_data)
    payload["provider"] = "chatgpt"

    if not payload.get("model"):
        payload["model"] = "unknown"

    return payload


# ---------------------------------------------------------------------------
# 5. Punto de entrada público
# ---------------------------------------------------------------------------


def extract_from_url(url: str) -> Dict[str, Any]:
    """Descarga y extrae una conversación compartida de ChatGPT a partir de una URL."""
    _validate_share_url(url)
    backend_data = _download_share_payload(url)
    payload = _extract_payload(backend_data)
    payload["conversation_url"] = url
    payload["url"] = url
    return payload


def extract_chatgpt_share(url: str) -> Dict[str, Any]:
    """Alias de compatibilidad para código existente."""
    return extract_from_url(url)
