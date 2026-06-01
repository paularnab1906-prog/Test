"""Prompt Director tests — offline imagination + style-following (no key, no network)."""
import pytest

from app.llm.director import PromptDirector, _sanitize


def test_sanitize_strips_meta_preamble():
    # the real leak observed from a weaker model
    leak = "Send the prompt only.\n\nA lonely lighthouse at dusk, slow drone orbit."
    out = _sanitize(leak)
    assert out.startswith("A lonely lighthouse")
    assert "Send the prompt" not in out


def test_sanitize_preserves_legit_prompt_and_unwraps_quotes():
    assert _sanitize('"a fox, cinematic, 35mm"') == "a fox, cinematic, 35mm"
    legit = "A lighthouse at dusk, golden light, photoreal."
    assert _sanitize(legit) == legit
    assert _sanitize("Prompt: a fox in a city") == "a fox in a city"


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
