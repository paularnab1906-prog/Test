"""OpenRouter image provider — real text-to-image via OpenRouter, plus stub.

OpenRouter can generate images with image-capable models (e.g. Gemini "Nano
Banana"). Unlike fal/Replicate this is synchronous: the image comes back in the
chat-completions response as a base64 data URL, so submit() does the call and
poll() returns the cached result immediately.

OpenRouter has NO video generation — this adapter only serves image capabilities.
"""
from __future__ import annotations

import uuid

import httpx

from app.config import get_settings
from app.providers.base import (
    NormalizedRequest,
    ProviderResult,
    ProviderState,
    ProviderStatus,
)

_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
_STUB_IMAGE = "https://picsum.photos/seed/lumina-or/768/1024"


class OpenRouterImageAdapter:
    name = "openrouter"

    def __init__(self) -> None:
        # ref -> ProviderStatus, populated by submit() (synchronous generation).
        self._results: dict[str, ProviderStatus] = {}

    @property
    def _enabled(self) -> bool:
        return bool(get_settings().openrouter_api_key)

    def estimate_cost(self, req: NormalizedRequest) -> int:
        return 5

    async def submit(self, req: NormalizedRequest) -> str:
        ref = f"or-{uuid.uuid4()}"
        if not self._enabled or not req.capability.endswith("image"):
            # Stub (no key) or wrong capability (OpenRouter can't do video).
            self._results[ref] = ProviderStatus(
                state=ProviderState.succeeded,
                results=[ProviderResult(kind="image", url=_STUB_IMAGE, thumbnail_url=_STUB_IMAGE)],
            )
            return ref

        s = get_settings()
        model = req.model or s.openrouter_image_model
        payload = {
            "model": model,
            "modalities": ["image", "text"],
            "messages": [{"role": "user", "content": req.prompt}],
        }
        headers = {
            "Authorization": f"Bearer {s.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://lumina.local",
            "X-Title": "Lumina",
        }
        async with httpx.AsyncClient(timeout=120) as http:
            resp = await http.post(_ENDPOINT, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()

        results = _parse_image_output(data)
        self._results[ref] = (
            ProviderStatus(state=ProviderState.succeeded, results=results)
            if results
            else ProviderStatus(state=ProviderState.failed, error="openrouter: no image returned")
        )
        return ref

    async def poll(self, ref: str) -> ProviderStatus:
        return self._results.get(ref, ProviderStatus(state=ProviderState.failed, error="unknown ref"))


def _parse_image_output(data: dict) -> list[ProviderResult]:
    """Pull image data URLs from an OpenRouter chat-completions response.

    Shape: choices[0].message.images[].image_url.url  (a data: URL, base64).
    """
    results: list[ProviderResult] = []
    for choice in data.get("choices", []) or []:
        message = choice.get("message", {}) or {}
        for img in message.get("images", []) or []:
            url = (img.get("image_url") or {}).get("url") if isinstance(img, dict) else None
            if url:
                results.append(ProviderResult(kind="image", url=url, thumbnail_url=url))
    return results
