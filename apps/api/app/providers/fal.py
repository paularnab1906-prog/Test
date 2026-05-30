"""fal.ai adapter.

Runs in two modes:
  * real    — when FAL_API_KEY is set, calls the fal queue API over HTTP.
  * stub     — when no key is configured, returns a deterministic placeholder
               asset so the whole pipeline is runnable end-to-end without spend.

The stub keeps Phase 0 fully exercisable; swap in real HTTP once you have a key.
"""
from __future__ import annotations

import asyncio
import uuid

from app.config import get_settings
from app.providers.base import (
    NormalizedRequest,
    ProviderResult,
    ProviderState,
    ProviderStatus,
)

# A tiny public sample video used only in stub mode.
_STUB_VIDEO = "https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerJoyrides.mp4"
_STUB_THUMB = "https://storage.googleapis.com/gtv-videos-bucket/sample/images/ForBiggerJoyrides.jpg"


class FalAdapter:
    name = "fal"

    def __init__(self) -> None:
        self._stub_jobs: dict[str, NormalizedRequest] = {}

    @property
    def _enabled(self) -> bool:
        return bool(get_settings().fal_api_key)

    def estimate_cost(self, req: NormalizedRequest) -> int:
        # Placeholder pricing: video costs more than image. Cents.
        return 50 if req.capability.endswith("video") else 5

    async def submit(self, req: NormalizedRequest) -> str:
        if not self._enabled:
            ref = f"stub-{uuid.uuid4()}"
            self._stub_jobs[ref] = req
            return ref
        # Real path (sketch): POST to the fal queue endpoint and return its
        # request_id. Wired up when FAL_API_KEY is provided.
        raise NotImplementedError("real fal submit() — implement with httpx + FAL_API_KEY")

    async def poll(self, ref: str) -> ProviderStatus:
        if ref.startswith("stub-"):
            # Pretend generation took a moment, then succeed.
            await asyncio.sleep(0)
            return ProviderStatus(
                state=ProviderState.succeeded,
                results=[ProviderResult(kind="video", url=_STUB_VIDEO, thumbnail_url=_STUB_THUMB)],
            )
        raise NotImplementedError("real fal poll() — implement with httpx + FAL_API_KEY")
