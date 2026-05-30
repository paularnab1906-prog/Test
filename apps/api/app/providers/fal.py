"""fal.ai adapter — real queue API + offline stub.

Modes:
  * real — when FAL_API_KEY is set: submits to the fal queue, polls status,
           fetches the result, and normalizes the output assets.
  * stub — when no key is configured: returns a deterministic placeholder so the
           whole pipeline runs without spend.

fal queue protocol (https://docs.fal.ai/model-endpoints/queue):
  POST   {QUEUE}/{model}                          -> {request_id, ...}
  GET    {QUEUE}/{model}/requests/{id}/status     -> {status: IN_QUEUE|IN_PROGRESS|COMPLETED}
  GET    {QUEUE}/{model}/requests/{id}            -> model output JSON
"""
from __future__ import annotations

import asyncio
import uuid

import httpx

from app.config import get_settings
from app.providers.base import (
    NormalizedRequest,
    ProviderResult,
    ProviderState,
    ProviderStatus,
)

_QUEUE = "https://queue.fal.run"

# Tiny public samples used only in stub mode.
_STUB_VIDEO = "https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerJoyrides.mp4"
_STUB_THUMB = "https://storage.googleapis.com/gtv-videos-bucket/sample/images/ForBiggerJoyrides.jpg"
_STUB_IMAGE = "https://picsum.photos/seed/lumina-fal/768/1024"

# aspect_ratio -> flux image_size enum
_IMAGE_SIZE = {
    "1:1": "square_hd",
    "16:9": "landscape_16_9",
    "9:16": "portrait_16_9",
    "4:3": "landscape_4_3",
    "3:4": "portrait_4_3",
}


class FalAdapter:
    name = "fal"

    def __init__(self) -> None:
        self._stub_jobs: dict[str, NormalizedRequest] = {}

    @property
    def _enabled(self) -> bool:
        return bool(get_settings().fal_api_key)

    def estimate_cost(self, req: NormalizedRequest) -> int:
        return 50 if req.capability.endswith("video") else 5

    # --- submit -----------------------------------------------------------
    async def submit(self, req: NormalizedRequest) -> str:
        if not self._enabled:
            ref = f"stub-{uuid.uuid4()}"
            self._stub_jobs[ref] = req
            return ref

        body = _fal_input(req)
        async with httpx.AsyncClient(timeout=60) as http:
            resp = await http.post(
                f"{_QUEUE}/{req.model}", headers=self._headers(), json=body
            )
            resp.raise_for_status()
            request_id = resp.json()["request_id"]
        # Encode the model so poll() can rebuild the status/result URLs.
        return f"{req.model}|{request_id}"

    # --- poll -------------------------------------------------------------
    async def poll(self, ref: str) -> ProviderStatus:
        if ref.startswith("stub-"):
            await asyncio.sleep(0)
            req = self._stub_jobs.get(ref)
            return ProviderStatus(state=ProviderState.succeeded, results=[_stub_result(req)])

        model, request_id = ref.split("|", 1)
        base = f"{_QUEUE}/{model}/requests/{request_id}"
        async with httpx.AsyncClient(timeout=60) as http:
            status_resp = await http.get(f"{base}/status", headers=self._headers())
            status_resp.raise_for_status()
            status = status_resp.json().get("status")

            if status != "COMPLETED":
                return ProviderStatus(state=ProviderState.running)

            result_resp = await http.get(base, headers=self._headers())
            result_resp.raise_for_status()
            output = result_resp.json()

        results = _parse_fal_output(output)
        if not results:
            return ProviderStatus(state=ProviderState.failed, error="fal: empty output")
        return ProviderStatus(state=ProviderState.succeeded, results=results)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Key {get_settings().fal_api_key}",
            "Content-Type": "application/json",
        }


def _fal_input(req: NormalizedRequest) -> dict:
    """Map our NormalizedRequest onto the model's native input schema."""
    p = req.params
    if req.capability.endswith("image"):
        body: dict = {
            "prompt": req.prompt,
            "num_images": int(p.get("num_images", 1)),
            "image_size": _IMAGE_SIZE.get(p.get("aspect_ratio", "1:1"), "square_hd"),
        }
        return body
    # video
    body = {"prompt": req.prompt}
    if req.image_url:
        body["image_url"] = req.image_url
    if "duration_s" in p:
        body["duration"] = str(p["duration_s"])
    if "aspect_ratio" in p:
        body["aspect_ratio"] = p["aspect_ratio"]
    return body


def _parse_fal_output(output: dict) -> list[ProviderResult]:
    """Normalize fal's varied output shapes into ProviderResults."""
    results: list[ProviderResult] = []
    # video: {"video": {"url": ...}}
    video = output.get("video")
    if isinstance(video, dict) and video.get("url"):
        results.append(ProviderResult(kind="video", url=video["url"]))
    # images: {"images": [{"url": ...}, ...]}
    for img in output.get("images", []) or []:
        url = img.get("url") if isinstance(img, dict) else img
        if url:
            results.append(ProviderResult(kind="image", url=url, thumbnail_url=url))
    return results


def _stub_result(req: NormalizedRequest | None) -> ProviderResult:
    if req is not None and req.capability.endswith("image"):
        return ProviderResult(kind="image", url=_STUB_IMAGE, thumbnail_url=_STUB_IMAGE)
    return ProviderResult(kind="video", url=_STUB_VIDEO, thumbnail_url=_STUB_THUMB)
