"""OpenRouter client — unified access to many text LLMs via one OpenAI-compatible API.

Two modes:
  * real — when OPENROUTER_API_KEY is set, calls the OpenRouter chat-completions API.
  * stub — when no key is configured, returns a deterministic enhanced prompt so the
           feature is exercisable without spend.
"""
from __future__ import annotations

import httpx

from app.config import get_settings

_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"

_SYSTEM = (
    "You are a prompt engineer for a cinematic AI media generator. "
    "Rewrite the user's idea into a single vivid, concrete prompt with strong "
    "visual detail (subject, setting, lighting, lens, mood). Keep it under 60 "
    "words. Return only the prompt text, no preamble."
)

# Descriptors appended in stub mode so the feature visibly does something offline.
_STUB_DESCRIPTORS = "cinematic lighting, shallow depth of field, 35mm film, rich color grade, highly detailed"


class OpenRouterClient:
    @property
    def _enabled(self) -> bool:
        return bool(get_settings().openrouter_api_key)

    async def enhance(self, prompt: str, capability: str) -> str:
        prompt = prompt.strip()
        if not self._enabled:
            return f"{prompt}, {_STUB_DESCRIPTORS}"
        return await self._complete(
            [
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": f"Idea ({capability}): {prompt}"},
            ]
        )

    async def _complete(self, messages: list[dict]) -> str:
        s = get_settings()
        headers = {
            "Authorization": f"Bearer {s.openrouter_api_key}",
            "Content-Type": "application/json",
            # Optional attribution headers OpenRouter recommends:
            "HTTP-Referer": "https://lumina.local",
            "X-Title": "Lumina",
        }
        payload = {"model": s.openrouter_model, "messages": messages, "max_tokens": 200}
        async with httpx.AsyncClient(timeout=30) as http:
            resp = await http.post(_ENDPOINT, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
