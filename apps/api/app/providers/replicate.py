"""Replicate adapter — real predictions API + offline stub.

Used both as a primary provider and as presets' `fallback` target, so the worker
can fail over when fal is unavailable.

Replicate protocol (https://replicate.com/docs/reference/http):
  POST {API}/models/{owner}/{model}/predictions  body {input}  -> {id, status, urls}
  GET  {API}/predictions/{id}                                   -> {status, output}
status: starting | processing | succeeded | failed | canceled
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

_API = "https://api.replicate.com/v1"

_STUB_VIDEO = "https://storage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4"
_STUB_THUMB = "https://storage.googleapis.com/gtv-videos-bucket/sample/images/ForBiggerEscapes.jpg"
_STUB_IMAGE = "https://picsum.photos/seed/lumina-rep/768/1024"


class ReplicateAdapter:
    name = "replicate"

    def __init__(self) -> None:
        self._stub_jobs: dict[str, NormalizedRequest] = {}
        # request_id -> capability, so poll() can label the output asset kind.
        self._caps: dict[str, str] = {}

    @property
    def _enabled(self) -> bool:
        return bool(get_settings().replicate_api_token)

    def estimate_cost(self, req: NormalizedRequest) -> int:
        return 60 if req.capability.endswith("video") else 6

    # --- submit -----------------------------------------------------------
    async def submit(self, req: NormalizedRequest) -> str:
        if not self._enabled:
            ref = f"stub-{uuid.uuid4()}"
            self._stub_jobs[ref] = req
            return ref

        body = {"input": _replicate_input(req)}
        async with httpx.AsyncClient(timeout=60) as http:
            resp = await http.post(
                f"{_API}/models/{req.model}/predictions", headers=self._headers(), json=body
            )
            resp.raise_for_status()
            prediction_id = resp.json()["id"]
        self._caps[prediction_id] = req.capability
        return prediction_id

    # --- poll -------------------------------------------------------------
    async def poll(self, ref: str) -> ProviderStatus:
        if ref.startswith("stub-"):
            await asyncio.sleep(0)
            req = self._stub_jobs.get(ref)
            return ProviderStatus(state=ProviderState.succeeded, results=[_stub_result(req)])

        async with httpx.AsyncClient(timeout=60) as http:
            resp = await http.get(f"{_API}/predictions/{ref}", headers=self._headers())
            resp.raise_for_status()
            data = resp.json()

        status = data.get("status")
        if status in ("starting", "processing"):
            return ProviderStatus(state=ProviderState.running)
        if status != "succeeded":
            return ProviderStatus(
                state=ProviderState.failed, error=data.get("error") or f"replicate: {status}"
            )

        kind = "video" if self._caps.get(ref, "").endswith("video") else "image"
        results = _parse_replicate_output(data.get("output"), kind)
        if not results:
            return ProviderStatus(state=ProviderState.failed, error="replicate: empty output")
        return ProviderStatus(state=ProviderState.succeeded, results=results)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {get_settings().replicate_api_token}",
            "Content-Type": "application/json",
        }


def _replicate_input(req: NormalizedRequest) -> dict:
    p = req.params
    if req.capability.endswith("image"):
        return {
            "prompt": req.prompt,
            "num_outputs": int(p.get("num_images", 1)),
            "aspect_ratio": p.get("aspect_ratio", "1:1"),
        }
    body: dict = {"prompt": req.prompt}
    if req.image_url:
        # MiniMax/Hailuo names the conditioning frame this way.
        body["first_frame_image"] = req.image_url
    return body


def _parse_replicate_output(output, kind: str) -> list[ProviderResult]:
    """Replicate output is a URL string or a list of URL strings."""
    urls: list[str] = []
    if isinstance(output, str):
        urls = [output]
    elif isinstance(output, list):
        urls = [u for u in output if isinstance(u, str)]
    return [
        ProviderResult(kind=kind, url=u, thumbnail_url=u if kind == "image" else None)
        for u in urls
    ]


def _stub_result(req: NormalizedRequest | None) -> ProviderResult:
    if req is not None and req.capability.endswith("image"):
        return ProviderResult(kind="image", url=_STUB_IMAGE, thumbnail_url=_STUB_IMAGE)
    return ProviderResult(kind="video", url=_STUB_VIDEO, thumbnail_url=_STUB_THUMB)
