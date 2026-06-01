"""Live smoke test for BytePlus ModelArk (ByteDance Ark) video generation.

Run on a network-enabled machine (the cloud sandbox blocks bytepluses.com):

    cd apps/api
    python scripts/smoke_byteplus_video.py "a lonely lighthouse at dusk"

Saves the result to apps/api/out.mp4. Stdlib only. Reads from env or the
gitignored apps/api/.env:
    BYTEPLUS_API_KEY=...                 (required)
    BYTEPLUS_VIDEO_MODEL=seedance-1-5-pro-251215
    BYTEPLUS_BASE_URL=https://ark.ap-southeast.bytepluses.com/api/v3
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


def _load() -> tuple[str, str, str]:
    env_file = Path(__file__).resolve().parent.parent / ".env"
    pairs = {}
    if env_file.exists():
        pairs = dict(re.findall(r"^(\w+)=(.*)$", env_file.read_text(), re.M))
    key = os.environ.get("BYTEPLUS_API_KEY") or pairs.get("BYTEPLUS_API_KEY")
    model = os.environ.get("BYTEPLUS_VIDEO_MODEL") or pairs.get(
        "BYTEPLUS_VIDEO_MODEL", "seedance-1-5-pro-251215"
    )
    base = os.environ.get("BYTEPLUS_BASE_URL") or pairs.get(
        "BYTEPLUS_BASE_URL", "https://ark.ap-southeast.bytepluses.com/api/v3"
    )
    if not key:
        sys.exit("No BYTEPLUS_API_KEY in environment or apps/api/.env")
    return key.strip(), model.strip(), base.strip()


def _req(url, key, method="GET", body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(
        url, data=data, method=method,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    try:
        return json.load(urllib.request.urlopen(r, timeout=60))
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode()[:500]}")


def main() -> None:
    prompt = sys.argv[1] if len(sys.argv) > 1 else "a lonely lighthouse at dusk, cinematic, slow push in"
    key, model, base = _load()
    print(f"model: {model}\nprompt: {prompt}\nsubmitting...")

    job = _req(
        f"{base}/contents/generations/tasks", key, "POST",
        {"model": model, "content": [{"type": "text", "text": prompt}]},
    )
    task_id = job.get("id") or job.get("task_id")
    if not task_id:
        sys.exit(f"no task id in create response: {json.dumps(job)[:400]}")
    print("task id:", task_id, "- polling (up to ~5 min)...")

    deadline = time.time() + 300
    while time.time() < deadline:
        st = _req(f"{base}/contents/generations/tasks/{task_id}", key)
        status = (st.get("status") or "").lower()
        print("  status:", status)
        if status == "succeeded":
            url = (st.get("content") or {}).get("video_url")
            if not url:
                sys.exit(f"succeeded but no video_url. raw: {json.dumps(st)[:500]}")
            out = Path(__file__).resolve().parent.parent / "out.mp4"
            out.write_bytes(urllib.request.urlopen(url, timeout=120).read())
            print(f"OK — saved video to {out}")
            print("usage:", st.get("usage"))
            return
        if status in ("failed", "cancelled", "canceled", "expired"):
            sys.exit(f"terminal status {status}: {st.get('error')}")
        time.sleep(6)
    sys.exit("timed out after 5 minutes")


if __name__ == "__main__":
    main()
