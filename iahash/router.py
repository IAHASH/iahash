"""Router de extractores para conversaciones compartidas."""

from __future__ import annotations

from urllib.parse import urlparse
from typing import Dict, Any

from .exceptions import UnsupportedProvider, InvalidShareURL
from . import chatgpt_share
from . import claude_share


def extract_shared_conversation(url: str, model: str | None = None) -> Dict[str, Any]:
    """
    Decide qué extractor usar en función del modelo y/o del dominio de la URL.

    - model == "chatgpt"  -> extractor de ChatGPT
    - model == "claude"   -> extractor de Claude
    - si model es None se infiere por hostname
    """

    url = url.strip()
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    normalized_model = (model or "").strip().lower()

    # 1) Si viene modelo forzado, respetarlo
    if normalized_model == "chatgpt":
        # Aquí dejamos que el propio extractor de ChatGPT valide la URL.
        return chatgpt_share.extract_from_url(url)

    if normalized_model == "claude":
        # Aquí dejamos que el propio extractor de Claude valide la URL.
        return claude_share.extract_from_url(url)

    # 2) Si no hay modelo explícito, inferir por dominio
    if hostname in {"chatgpt.com", "www.chatgpt.com", "chat.openai.com", "www.chat.openai.com"}:
        return chatgpt_share.extract_from_url(url)

    if hostname in {"claude.ai", "www.claude.ai"}:
        return claude_share.extract_from_url(url)

    # 3) Si nada coincide, lanzamos error genérico
    raise UnsupportedProvider(
        f"URL no compatible: dominio '{hostname}' no soportado. "
        "Actualmente solo se admiten chatgpt.com / chat.openai.com y claude.ai."
    )