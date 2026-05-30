"""Prompt Director tests — offline imagination + style-following (no key, no network)."""
import pytest

from app.llm.director import PromptDirector


@pytest.mark.asyncio
async def test_imagines_scene_from_vague_idea():
    d = PromptDirector()  # no OPENROUTER_API_KEY -> offline heuristic
    out = await d.direct("a lonely lighthouse", "image_to_video", "camera-motion")
    assert "a lonely lighthouse" in out
    # imagined production detail is added
    assert "lens" in out and "lighting" in out
    assert len(out) > 80


@pytest.mark.asyncio
async def test_follows_user_examples():
    d = PromptDirector()
    out = await d.direct(
        "a lonely lighthouse",
        "text_to_image",
        "image",
        examples=["moody noir portrait, harsh chiaroscuro, smoky backlight"],
    )
    # distinctive words from the example leak into the style hint
    assert "style of" in out
    assert "chiaroscuro" in out or "noir" in out


@pytest.mark.asyncio
async def test_video_vs_image_differ():
    d = PromptDirector()
    vid = await d.direct("a fox", "image_to_video", "camera-motion")
    img = await d.direct("a fox", "text_to_image", "image")
    assert "fps" in vid or "anamorphic" in vid     # video-specific
    assert "composition" in img                     # image-specific
