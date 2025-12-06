"""Extractor for ChatGPT shared conversations."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional

import httpx

ERROR_UNREACHABLE = "UNREACHABLE"
ERROR_PARSING = "PARSING_ERROR"
ERROR_UNSUPPORTED = "UNSUPPORTED_FORMAT"


class ExtractedConversation(Dict[str, Any]):
    pass


def fetch_share_html(url: str) -> str:
    try:
        response = httpx.get(url, timeout=15)
        response.raise_for_status()
        return response.text
    except Exception as exc:
        raise RuntimeError(ERROR_UNREACHABLE) from exc


def parse_next_data(html: str) -> Optional[Dict[str, Any]]:
    match = re.search(r"<script id=\"__NEXT_DATA__\" type=\"application/json\">(.*?)</script>", html, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def extract_messages(next_data: Dict[str, Any]) -> tuple[Optional[str], Optional[str], Optional[str]]:
    try:
        conversation = next_data["props"]["pageProps"].get("sharedConversation") or next_data["props"]["pageProps"].get("serverResponse", {}).get("data", {})
    except Exception:
        conversation = None
    if not conversation:
        return None, None, None

    mapping = conversation.get("mapping") or {}
    user_messages = []
    assistant_messages = []
    for node in mapping.values():
        message = node.get("message") if isinstance(node, dict) else None
        if not message:
            continue
        author_role = (message.get("author") or {}).get("role")
        content_parts = message.get("content", {}).get("parts") or []
        text = "\n".join(part for part in content_parts if isinstance(part, str))
        if author_role == "user":
            user_messages.append(text)
        elif author_role == "assistant":
            assistant_messages.append(text)
    prompt_text = user_messages[0] if user_messages else None
    response_text = assistant_messages[-1] if assistant_messages else None
    model = conversation.get("modelSlug") or conversation.get("model")
    return prompt_text, response_text, model


def extract_chatgpt_share(url: str) -> ExtractedConversation:
    try:
        html = fetch_share_html(url)
    except RuntimeError as exc:
        return {"error": str(exc)}
    next_data = parse_next_data(html)
    if not next_data:
        return {"error": ERROR_UNSUPPORTED}

    prompt_text, response_text, model = extract_messages(next_data)
    if not prompt_text or not response_text:
        return {"error": ERROR_PARSING}

    return {
        "prompt_text": prompt_text,
        "response_text": response_text,
        "model": model or "unknown",
        "provider": "chatgpt",
        "conversation_url": url,
    }
