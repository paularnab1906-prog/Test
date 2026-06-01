"""OpenRouter video provider — real text/image-to-video via the async videos API.

OpenRouter added video generation (Veo, Sora, Seedance, Wan, Kling, ...). Unlike
chat/image it's an async job API:

  POST {API}/videos                 -> 202 {id, status, polling_url}
  GET  {API}/videos/{id}            -> {status, unsigned_urls, error, ...}
  status: queued/processing/... -> running; completed -> success;
          failed/cancelled/expired -> error

The final video lives in `unsigned_urls` (list of strings). When those point back
at the OpenRouter API they need the bearer token to download — handled in
app/storage.py.
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

_API = "https://openrouter.ai/api/v1/videos"
_STUB_VIDEO = "https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerMeltdowns.mp4"
_STUB_THUMB = "https://storage.googleapis.com/gtv-videos-bucket/sample/images/ForBiggerMeltdowns.jpg"

_TERMINAL_ERROR = {"failed", "cancelled", "canceled", "expired"}


class OpenRouterVideoAdapter:
    name = "openrouter_video"

    def __init__(self) -> None:
        self._stub_jobs: dict[str, NormalizedRequest] = {}

    @property
    def _enabled(self) -> bool:
        return bool(get_settings().openrouter_api_key)

    def estimate_cost(self, req: NormalizedRequest) -> int:
        return 80

    async def submit(self, req: NormalizedRequest) -> str:
        if not self._enabled or not req.capability.endswith("video"):
            ref = f"stub-{uuid.uuid4()}"
            self._stub_jobs[ref] = req
            return ref

        s = get_settings()
        body: dict = {"model": req.model or s.openrouter_video_model, "prompt": req.prompt}
        p = req.params
        if "aspect_ratio" in p:
            body["aspect_ratio"] = p["aspect_ratio"]
        if "duration_s" in p:
            body["duration"] = int(p["duration_s"])
        if req.image_url:
            # image-to-video: condition on the user's image as the first frame.
            body["frame_images"] = [{"frame_type": "first_frame", "image_url": req.image_url}]

        async with httpx.AsyncClient(timeout=60) as http:
            resp = await http.post(_API, headers=_headers(), json=body)
            resp.raise_for_status()
            return resp.json()["id"]

    async def poll(self, ref: str) -> ProviderStatus:
        if ref.startswith("stub-"):
            return ProviderStatus(
                state=ProviderState.succeeded,
                results=[ProviderResult(kind="video", url=_STUB_VIDEO, thumbnail_url=_STUB_THUMB)],
            )

        async with httpx.AsyncClient(timeout=60) as http:
            resp = await http.get(f"{_API}/{ref}", headers=_headers())
            resp.raise_for_status()
            data = resp.json()

        status = (data.get("status") or "").lower()
        if status == "completed":
            results = _parse_video_output(data)
            if results:
                return ProviderStatus(state=ProviderState.succeeded, results=results)
            return ProviderStatus(state=ProviderState.failed, error="openrouter: no video url")
        if status in _TERMINAL_ERROR:
            return ProviderStatus(
                state=ProviderState.failed, error=data.get("error") or f"openrouter: {status}"
            )
        return ProviderStatus(state=ProviderState.running)


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {get_settings().openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://lumina.local",
        "X-Title": "Lumina",
    }


def _parse_video_output(data: dict) -> list[ProviderResult]:
    urls = data.get("unsigned_urls") or []
    return [ProviderResult(kind="video", url=u) for u in urls if isinstance(u, str)]
