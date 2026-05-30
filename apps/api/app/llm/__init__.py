"""LLM layer — text models via OpenRouter.

Separate from `app.providers` (media generation). Used for the Prompt Director:
expanding a rough idea into a detailed, style-matched generation prompt. It does
NOT generate video/images — that always routes through the media providers.
"""
from __future__ import annotations

from collections.abc import Sequence

from app.llm.director import PromptDirector
from app.llm.openrouter import OpenRouterClient

_director = PromptDirector(OpenRouterClient())


async def direct_prompt(
    idea: str,
    capability: str,
    category: str = "",
    examples: Sequence[str] = (),
) -> str:
    """Imagine + detail a generation prompt from a rough idea, following examples."""
    return await _director.direct(idea, capability, category, examples)


async def enhance_prompt(prompt: str, capability: str) -> str:
    """Back-compat alias for a plain enhancement with no examples/category."""
    return await direct_prompt(prompt, capability)


__all__ = ["direct_prompt", "enhance_prompt", "PromptDirector", "OpenRouterClient"]
