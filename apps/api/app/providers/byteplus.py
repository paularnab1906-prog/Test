"""BytePlus ModelArk (ByteDance Ark) video provider.

Native Seedance access on ByteDance's own platform — useful for testing on the
free credit allotment instead of paying per clip elsewhere.

Ark content-generation tasks API (async):
  POST {BASE}/contents/generations/tasks          -> {id}
  GET  {BASE}/contents/generations/tasks/{id}     -> {status, content:{video_url}}
  status: queued | running | succeeded | failed | cancelled
Auth: Bearer <ARK_API_KEY>. Model e.g. "seedance-1-5-pro-251215".
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

_STUB_VIDEO = "https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4"
_STUB_THUMB = "https://storage.googleapis.com/gtv-videos-bucket/sample/images/ForBiggerBlazes.jpg"
_TERMINAL_ERROR = {"failed", "cancelled", "canceled", "expired"}


class BytePlusAdapter:
    name = "byteplus"

    def __init__(self) -> None:
        self._stub_jobs: dict[str, NormalizedRequest] = {}

    @property
    def _enabled(self) -> bool:
        return bool(get_settings().byteplus_api_key)

    def estimate_cost(self, req: NormalizedRequest) -> int:
        return 80

    async def submit(self, req: NormalizedRequest) -> str:
        if not self._enabled or not req.capability.endswith("video"):
            ref = f"stub-{uuid.uuid4()}"
            self._stub_jobs[ref] = req
            return ref

        s = get_settings()
        content: list[dict] = [{"type": "text", "text": req.prompt}]
        if req.image_url:
            # image-to-video: condition on the user's image as the first frame.
            content.append(
                {"type": "image_url", "image_url": {"url": req.image_url}, "role": "first_frame"}
            )
        body: dict = {"model": req.model or s.byteplus_video_model, "content": content}
        p = req.params
        if "aspect_ratio" in p:
            body["ratio"] = p["aspect_ratio"]
        if "duration_s" in p:
            body["duration"] = int(p["duration_s"])
        if "resolution" in p:
            body["resolution"] = p["resolution"]

        async with httpx.AsyncClient(timeout=60) as http:
            resp = await http.post(
                f"{s.byteplus_base_url}/contents/generations/tasks", headers=_headers(), json=body
            )
            resp.raise_for_status()
            data = resp.json()
        return data.get("id") or data.get("task_id")

    async def poll(self, ref: str) -> ProviderStatus:
        if ref.startswith("stub-"):
            return ProviderStatus(
                state=ProviderState.succeeded,
                results=[ProviderResult(kind="video", url=_STUB_VIDEO, thumbnail_url=_STUB_THUMB)],
            )

        s = get_settings()
        async with httpx.AsyncClient(timeout=60) as http:
            resp = await http.get(
                f"{s.byteplus_base_url}/contents/generations/tasks/{ref}", headers=_headers()
            )
            resp.raise_for_status()
            data = resp.json()

        status = (data.get("status") or "").lower()
        if status == "succeeded":
            results = _parse_output(data)
            if results:
                return ProviderStatus(state=ProviderState.succeeded, results=results)
            return ProviderStatus(state=ProviderState.failed, error="byteplus: no video_url")
        if status in _TERMINAL_ERROR:
            err = (data.get("error") or {})
            msg = err.get("message") if isinstance(err, dict) else err
            return ProviderStatus(state=ProviderState.failed, error=msg or f"byteplus: {status}")
        return ProviderStatus(state=ProviderState.running)


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {get_settings().byteplus_api_key}",
        "Content-Type": "application/json",
    }


def _parse_output(data: dict) -> list[ProviderResult]:
    content = data.get("content") or {}
    url = content.get("video_url") if isinstance(content, dict) else None
    return [ProviderResult(kind="video", url=url)] if url else []
