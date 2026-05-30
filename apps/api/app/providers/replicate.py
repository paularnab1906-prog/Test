"""Replicate adapter — hosts many video/image models (Kling, Wan, LTX, etc.).

Used both as a primary provider and as the `fallback` target in presets, so the
router can fail over when fal is unavailable. Stub mode when no token is set.
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

_STUB_VIDEO = "https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4"
_STUB_THUMB = "https://storage.googleapis.com/gtv-videos-bucket/sample/images/ForBiggerEscapes.jpg"


class ReplicateAdapter:
    name = "replicate"

    def __init__(self) -> None:
        self._stub_jobs: dict[str, NormalizedRequest] = {}

    @property
    def _enabled(self) -> bool:
        return bool(get_settings().replicate_api_token)

    def estimate_cost(self, req: NormalizedRequest) -> int:
        return 60 if req.capability.endswith("video") else 6

    async def submit(self, req: NormalizedRequest) -> str:
        if not self._enabled:
            ref = f"stub-{uuid.uuid4()}"
            self._stub_jobs[ref] = req
            return ref
        # Real path (sketch): POST to https://api.replicate.com/v1/predictions with
        # the model version + input, return prediction id. Wire up with the token.
        raise NotImplementedError("real replicate submit() — implement with httpx + token")

    async def poll(self, ref: str) -> ProviderStatus:
        if ref.startswith("stub-"):
            await asyncio.sleep(0)
            return ProviderStatus(
                state=ProviderState.succeeded,
                results=[ProviderResult(kind="video", url=_STUB_VIDEO, thumbnail_url=_STUB_THUMB)],
            )
        raise NotImplementedError("real replicate poll() — implement with httpx + token")
