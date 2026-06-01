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
        # Seedance takes parameters as `--` commands appended to the prompt text
        # (the "prompt manual"), not as top-level JSON fields.
        content: list[dict] = [{"type": "text", "text": _build_prompt(req)}]
        if req.image_url:
            # image-to-video: condition on the user's image as the first frame.
            content.append(
                {"type": "image_url", "image_url": {"url": req.image_url}, "role": "first_frame"}
            )
        body: dict = {"model": req.model or s.byteplus_video_model, "content": content}

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


def _build_prompt(req: NormalizedRequest) -> str:
    """Append Seedance prompt-manual `--` commands to the text prompt.

    Supported (per the Seedance 1.5 Pro prompt guide):
      --resolution 480p|720p|1080p   --ratio 1:1|3:4|4:3|16:9|9:16|21:9
      --duration 2..12               --camerafixed true|false
      --seed <int>

    Draft mode: there isn't a publicly-documented `--draft` flag, so we approximate
    the playground's "Draft mode" with the fast/cheap 480p profile. If your console's
    "Copy sample code" reveals a real draft field, we can send it verbatim instead.
    """
    p = req.params or {}
    text = req.prompt.strip()
    cmds: list[str] = []

    resolution = "480p" if p.get("draft") else p.get("resolution")
    if resolution:
        cmds.append(f"--resolution {resolution}")
    if p.get("aspect_ratio"):
        cmds.append(f"--ratio {p['aspect_ratio']}")
    if p.get("duration_s") is not None:
        cmds.append(f"--duration {max(2, min(12, int(p['duration_s'])))}")
    if "camerafixed" in p:
        cmds.append(f"--camerafixed {'true' if p['camerafixed'] else 'false'}")
    if p.get("seed") is not None:
        cmds.append(f"--seed {int(p['seed'])}")

    return f"{text} {' '.join(cmds)}".strip() if cmds else text


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {get_settings().byteplus_api_key}",
        "Content-Type": "application/json",
    }


def _parse_output(data: dict) -> list[ProviderResult]:
    content = data.get("content") or {}
    url = content.get("video_url") if isinstance(content, dict) else None
    return [ProviderResult(kind="video", url=url)] if url else []
