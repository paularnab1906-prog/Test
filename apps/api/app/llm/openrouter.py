"""OpenRouter transport — unified access to many text LLMs via one OpenAI-compatible API.

This module is just the wire protocol. The prompt-engineering logic (imagining a
scene, following the user's examples) lives in app/llm/director.py.

Two modes:
  * real — when OPENROUTER_API_KEY is set, calls the chat-completions API.
  * stub — when no key is configured, callers fall back to a local heuristic so
           the feature is exercisable without spend.
"""
from __future__ import annotations

import httpx

from app.config import get_settings

_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouterClient:
    @property
    def enabled(self) -> bool:
        return bool(get_settings().openrouter_api_key)

    async def complete(self, messages: list[dict], max_tokens: int = 320) -> str:
        s = get_settings()
        headers = {
            "Authorization": f"Bearer {s.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://lumina.local",
            "X-Title": "Lumina",
        }
        payload = {"model": s.openrouter_model, "messages": messages, "max_tokens": max_tokens}
        async with httpx.AsyncClient(timeout=30) as http:
            resp = await http.post(_ENDPOINT, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
