"""LLM layer tests — stub mode (no OPENROUTER_API_KEY), no network."""
import pytest

from app import llm


@pytest.mark.asyncio
async def test_enhance_prompt_stub_enriches():
    out = await llm.enhance_prompt("a fox in a city", "image_to_video")
    assert "a fox in a city" in out
    # stub appends cinematic descriptors
    assert "cinematic" in out.lower()
    assert len(out) > len("a fox in a city")
