"""LLM layer — text models via OpenRouter.

This is deliberately separate from `app.providers` (which is for media/video/image
generation). OpenRouter is a unified gateway over many *text* LLMs; we use it for
prompt enhancement, captioning, and (later) safety pre-screening. It does NOT
generate video — that always routes through the media providers.
"""
from __future__ import annotations

from app.llm.openrouter import OpenRouterClient

_client = OpenRouterClient()


async def enhance_prompt(prompt: str, capability: str) -> str:
    """Expand a short user prompt into a richer, cinematic generation prompt."""
    return await _client.enhance(prompt, capability)


__all__ = ["enhance_prompt", "OpenRouterClient"]
