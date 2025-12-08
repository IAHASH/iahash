"""
Extractor for Claude shared conversations.

Este módulo descarga una página pública de conversación compartida de Claude
(https://claude.ai/share/<id>), extrae el JSON embebido (formato Next.js) y
reconstruye el primer prompt de usuario y la primera respuesta del asistente en
el formato esperado por IA-HASH.

El parser está diseñado para ser relativamente robusto frente a cambios de
estructura, buscando de forma recursiva una lista de mensajes que tengan
campos tipo ``role`` y ``content`` en lugar de depender de una ruta rígida.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence
from urllib.parse import urlparse

import httpx

from iahash.extractors.exceptions import (
    InvalidShareURL,
    UnreachableSource,
    UnsupportedProvider,
)

__all__ = ["extract_from_url"]


# --- URL & descarga ---------------------------------------------------------


CLAUDE_SHARE_HOSTS = {
    "claude.ai",
    "www.claude.ai",
}

CLAUDE_SHARE_PATH_PREFIX = "/share/"


def _validate_share_url(url: str) -> None:
    """Validar que la URL apunta a una conversación compartida de Claude."""
    parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"}:
        raise InvalidShareURL(
            "URL inválida. Debe usar http(s)://claude.ai/share/..."
        )

    hostname = (parsed.hostname or "").lower()
    if hostname not in CLAUDE_SHARE_HOSTS:
        raise InvalidShareURL("URL inválida. Debe usar claude.ai")

    if not parsed.path.startswith(CLAUDE_SHARE_PATH_PREFIX):
        raise InvalidShareURL(
            "URL inválida. La ruta debe comenzar con /share/"
        )

    share_id = parsed.path[len(CLAUDE_SHARE_PATH_PREFIX) :].strip("/")
    if not share_id:
        raise InvalidShareURL(
            "URL inválida. Falta el identificador de la conversación compartida"
        )


def _download_html(url: str, *, timeout: float = 10.0) -> str:
    """Descargar el HTML de la página de share de Claude."""
    headers = {
        # User-Agent tipo navegador para reducir la probabilidad de bloqueos
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    try:
        response = httpx.get(
            url,
            timeout=timeout,
            follow_redirects=True,
            headers=headers,
        )
    except httpx.HTTPError as exc:  # pragma: no cover - defensivo
        raise UnreachableSource(
            f"Connection error when fetching Claude share URL: {exc}"
        ) from exc

    if response.status_code < 200 or response.status_code >= 300:
        raise UnreachableSource(
            f"HTTP {response.status_code} when fetching Claude share URL"
        )

    return response.text


# --- Extracción de JSON (__NEXT_DATA__) -------------------------------------


def _extract_next_data(html: str) -> Dict[str, Any]:
    """
    Extraer y parsear el JSON de ``__NEXT_DATA__`` de la página de Claude.

    Claude usa Next.js, por lo que el HTML de share incluye un bloque:

        <script id="__NEXT_DATA__" type="application/json"> ... </script>
    """
    # Buscamos el script con id="__NEXT_DATA__"
    match = re.search(
        r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
        html,
        re.DOTALL | re.IGNORECASE,
    )
    if not match:
        raise UnsupportedProvider(
            "Could not find __NEXT_DATA__ script in Claude share page"
        )

    raw_json = match.group(1).strip()
    try:
        return json.loads(raw_json)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensivo
        raise UnsupportedProvider(
            "Could not parse __NEXT_DATA__ JSON in Claude share page"
        ) from exc


# --- Búsqueda de mensajes & modelo ------------------------------------------


def _find_messages_list(obj: Any) -> Optional[Sequence[Dict[str, Any]]]:
    """
    Buscar recursivamente una lista de mensajes tipo Claude.

    Un candidato válido es una lista en la que cada elemento es un dict con
    al menos las claves ``role`` y ``content``.
    """
    if isinstance(obj, dict):
        # Candidato directo: key "messages"
        messages = obj.get("messages")
        if isinstance(messages, list) and messages and all(
            isinstance(m, dict) and "role" in m and "content" in m
            for m in messages
        ):
            return messages  # type: ignore[return-value]

        # Buscar en valores hijos
        for value in obj.values():
            found = _find_messages_list(value)
            if found is not None:
                return found

    elif isinstance(obj, list):
        for item in obj:
            found = _find_messages_list(item)
            if found is not None:
                return found

    return None


def _message_text(message: Dict[str, Any]) -> str:
    """
    Extraer texto plano de un mensaje de Claude.

    Claude suele usar estructuras como:
        {"content": [{"type": "text", "text": "…"}]}
    pero este helper intenta ser tolerante con variaciones.
    """
    content = message.get("content")

    # Caso directo: string
    if isinstance(content, str):
        return content.strip()

    parts: List[str] = []

    def _extract_from_part(part: Any) -> None:
        if isinstance(part, str):
            if part.strip():
                parts.append(part.strip())
            return
        if isinstance(part, dict):
            # Campos típicos
            for key in ("text", "content", "data"):
                val = part.get(key)
                if isinstance(val, str) and val.strip():
                    parts.append(val.strip())
                    return

    if isinstance(content, list):
        for part in content:
            _extract_from_part(part)
    elif isinstance(content, dict):
        _extract_from_part(content)

    return "\n".join(parts).strip()


def _collect_first_pair(
    messages: Sequence[Dict[str, Any]],
) -> tuple[str, str]:
    """
    Recoger el primer prompt de usuario y la primera respuesta del asistente.

    - Usuario: roles típicos "user" o "human".
    - Asistente: roles "assistant" o "ai".
    """
    user_roles = {"user", "human"}
    assistant_roles = {"assistant", "ai"}

    user_index: Optional[int] = None

    for idx, msg in enumerate(messages):
        role = str(msg.get("role") or "").lower()
        if role in user_roles:
            user_index = idx
            break

    if user_index is None:
        raise UnsupportedProvider(
            "Could not find user message in Claude shared conversation"
        )

    # Primer assistant después del user encontrado
    assistant_index: Optional[int] = None
    for idx in range(user_index + 1, len(messages)):
        role = str(messages[idx].get("role") or "").lower()
        if role in assistant_roles:
            assistant_index = idx
            break

    if assistant_index is None:
        raise UnsupportedProvider(
            "Could not find assistant response in Claude shared conversation"
        )

    prompt_text = _message_text(messages[user_index])
    response_text = _message_text(messages[assistant_index])

    if not prompt_text or not response_text:
        raise UnsupportedProvider(
            "Claude shared conversation has empty prompt or response content"
        )

    return prompt_text, response_text


def _find_first_value(obj: Any, keys: set[str]) -> Optional[Any]:
    """Buscar recursivamente el primer valor cuyo key esté en ``keys``."""
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
    """Extraer prompt, respuesta y modelo a partir de los datos Next.js."""
    messages = _find_messages_list(next_data)
    if not messages:
        raise UnsupportedProvider(
            "Could not find messages list in Claude share data"
        )

    prompt_text, response_text = _collect_first_pair(messages)

    # Intentamos obtener el modelo; Claude suele incluirlo en el mensaje
    # del asistente o en metadatos superiores.
    model = _find_first_value(
        next_data,
        {"model", "modelSlug", "model_slug", "model_name", "modelId", "model_id"},
    )
    if not isinstance(model, str) or not model.strip():
        model = "unknown"

    return {
        "prompt_text": prompt_text,
        "response_text": response_text,
        "model": model,
    }


# --- API pública ------------------------------------------------------------


def extract_from_url(url: str) -> Dict[str, Any]:
    """
    Descargar y extraer una conversación compartida de Claude a partir de su URL.

    Devuelve un diccionario con:
        - prompt_text
        - response_text
        - model
        - provider = "claude"
        - conversation_url / url
    """
    _validate_share_url(url)
    html = _download_html(url)
    next_data = _extract_next_data(html)
    payload = _conversation_payload(next_data)

    payload_out: Dict[str, Any] = dict(payload)
    payload_out["provider"] = "claude"
    payload_out["conversation_url"] = url
    payload_out["url"] = url
    return payload_out