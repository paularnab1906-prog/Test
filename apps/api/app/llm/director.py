"""Prompt Director — turns a rough idea into a detailed, production-ready prompt.

Goals (from the product spec):
  * Imagine the scene even when the user under-describes it: fill in subject,
    setting, time of day, lighting, lens, camera, mood, and palette.
  * Follow the user's examples — both explicit examples passed in and the user's
    own recent successful generations — so output matches their taste/style.
  * Produce specific, detailed prompting tuned to the capability (image vs video).

When OpenRouter is configured this is done by an LLM with few-shot examples.
Without a key, a local heuristic produces a detailed prompt so the feature still
works offline (and as a deterministic fallback if the LLM call fails).
"""
from __future__ import annotations

from collections.abc import Sequence

from app.llm.openrouter import OpenRouterClient

_SYSTEM = """You are the Prompt Director for a cinematic AI media generator.
Your job: transform a user's idea — however brief or vague — into ONE vivid,
concrete generation prompt that produces a stunning result.

Rules:
- If the user is vague, IMAGINE the missing details and commit to specific
  choices: subject, setting, time of day, lighting, lens/camera, mood, color
  palette, and composition. Never ask questions; decide.
- Study the EXAMPLES (the user's own style). Match their tone, level of detail,
  and aesthetic. Do not copy their content — adopt their style.
- For video, include camera movement and what unfolds in the shot.
- For image, include composition, framing, and lighting.
- Keep it to a single paragraph under ~70 words. Output ONLY the prompt text —
  no preamble, no quotes, no lists."""

# Heuristic vocabulary for the offline/fallback "imagination".
_LIGHTING = "soft directional lighting with gentle rim light"
_PALETTE = "rich teal-and-amber color grade"
_VIDEO_SCAFFOLD = (
    "{idea}. {motion} A cinematic shot at golden hour, {lighting}, shallow depth "
    "of field on a 35mm anamorphic lens, atmospheric haze, {palette}, "
    "highly detailed, photoreal, 24fps film look"
)
_IMAGE_SCAFFOLD = (
    "{idea}. Cinematic still, balanced rule-of-thirds composition, {lighting}, "
    "85mm portrait lens, fine texture and skin detail, {palette}, "
    "editorial photography, high dynamic range, photoreal"
)
# Category-specific motion phrasing for the video heuristic.
_MOTION_BY_CATEGORY = {
    "camera-motion": "The camera glides with deliberate cinematic motion.",
}
_DEFAULT_MOTION = "Subtle, lifelike motion fills the frame."


class PromptDirector:
    def __init__(self, client: OpenRouterClient | None = None) -> None:
        self._client = client or OpenRouterClient()

    async def direct(
        self,
        idea: str,
        capability: str,
        category: str = "",
        examples: Sequence[str] = (),
    ) -> str:
        idea = idea.strip()
        if not idea:
            return idea
        if not self._client.enabled:
            return self._imagine(idea, capability, category, examples)
        try:
            return await self._client.complete(
                self._build_messages(idea, capability, category, examples)
            )
        except Exception:
            # Never fail a generation because enhancement failed — degrade gracefully.
            return self._imagine(idea, capability, category, examples)

    # --- LLM path ---------------------------------------------------------
    def _build_messages(
        self, idea: str, capability: str, category: str, examples: Sequence[str]
    ) -> list[dict]:
        messages: list[dict] = [{"role": "system", "content": _SYSTEM}]
        # Few-shot: show the user's own style as prior assistant outputs.
        for ex in list(examples)[:4]:
            ex = ex.strip()
            if ex:
                messages.append({"role": "user", "content": "Idea: (example of my style)"})
                messages.append({"role": "assistant", "content": ex})
        ctx = f"capability={capability}"
        if category:
            ctx += f", style={category}"
        messages.append({"role": "user", "content": f"Idea ({ctx}): {idea}"})
        return messages

    # --- offline / fallback path -----------------------------------------
    def _imagine(
        self, idea: str, capability: str, category: str, examples: Sequence[str]
    ) -> str:
        is_video = capability.endswith("video")
        scaffold = _VIDEO_SCAFFOLD if is_video else _IMAGE_SCAFFOLD
        prompt = scaffold.format(
            idea=idea.rstrip("."),
            motion=_MOTION_BY_CATEGORY.get(category, _DEFAULT_MOTION),
            lighting=_LIGHTING,
            palette=_PALETTE,
        )
        # Lightly fold in the user's style by borrowing distinctive words from
        # their examples (offline approximation of "follow the examples").
        style = _style_hint(examples)
        if style:
            prompt += f", {style}"
        return prompt


def _style_hint(examples: Sequence[str]) -> str:
    """Extract a few distinctive descriptive words from the user's examples."""
    stop = {
        "the", "a", "an", "and", "with", "of", "in", "on", "at", "to", "for",
        "shot", "scene", "cinematic", "prompt", "video", "image", "style",
    }
    seen: list[str] = []
    for ex in examples:
        for raw in ex.lower().replace(",", " ").split():
            w = raw.strip(".")
            if len(w) > 4 and w not in stop and w not in seen:
                seen.append(w)
    return "in the style of " + ", ".join(seen[:5]) if seen else ""
