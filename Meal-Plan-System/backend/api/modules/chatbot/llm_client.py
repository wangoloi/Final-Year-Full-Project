"""OpenAI-compatible or Ollama HTTP chat for RAG replies."""
from __future__ import annotations

import logging
from typing import List

import httpx

from api.core import config

logger = logging.getLogger(__name__)


def is_llm_configured() -> bool:
    return bool(config.OPENAI_API_KEY) or bool(config.OLLAMA_HOST)


def chat(messages: List[dict]) -> str:
    """
    messages: [{"role": "system"|"user"|"assistant", "content": "..."}, ...]
    Prefers OpenAI when OPENAI_API_KEY is set; otherwise Ollama if OLLAMA_HOST is set.
    """
    if config.OPENAI_API_KEY:
        return _openai_chat(messages)
    if config.OLLAMA_HOST:
        return _ollama_chat(messages)
    raise RuntimeError("No LLM configured (set OPENAI_API_KEY or OLLAMA_HOST)")


def _openai_chat(messages: List[dict]) -> str:
    url = f"{config.OPENAI_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": config.CHATBOT_MODEL,
        "messages": messages,
        "temperature": 0.35,
        "max_tokens": 600,
    }
    with httpx.Client(timeout=120.0) as client:
        r = client.post(url, headers=headers, json=body)
        r.raise_for_status()
        data = r.json()
    content = data["choices"][0]["message"]["content"]
    return (content or "").strip()


def _ollama_chat(messages: List[dict]) -> str:
    url = f"{config.OLLAMA_HOST}/api/chat"
    body = {
        "model": config.OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.35, "num_predict": 600},
    }
    with httpx.Client(timeout=120.0) as client:
        r = client.post(url, json=body)
        r.raise_for_status()
        data = r.json()
    msg = data.get("message") or {}
    content = msg.get("content") or ""
    return content.strip()
