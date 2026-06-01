"""Live smoke test for OpenRouter video generation (async API).

Run on a network-enabled machine (the cloud sandbox blocks openrouter.ai):

    cd apps/api
    # 1) list available video models + their slugs:
    python scripts/smoke_openrouter_video.py --list
    # 2) generate a clip (uses OPENROUTER_VIDEO_MODEL, or pass --model):
    python scripts/smoke_openrouter_video.py "a lonely lighthouse at dusk"
    python scripts/smoke_openrouter_video.py "..." --model google/veo-3.1

Saves the result to apps/api/out.mp4. Stdlib only. Key + model from env or the
gitignored apps/api/.env.

NOTE: video models cost real money and take time. This polls up to ~5 minutes.
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

BASE = "https://openrouter.ai/api/v1/videos"


def _load() -> tuple[str, str]:
    key = os.environ.get("OPENROUTER_API_KEY")
    model = os.environ.get("OPENROUTER_VIDEO_MODEL", "google/veo-3.1")
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if (not key) and env_file.exists():
        pairs = dict(re.findall(r"^(\w+)=(.*)$", env_file.read_text(), re.M))
        key = pairs.get("OPENROUTER_API_KEY")
        model = pairs.get("OPENROUTER_VIDEO_MODEL", model)
    if not key:
        sys.exit("No OPENROUTER_API_KEY in environment or apps/api/.env")
    return key.strip(), model.strip()


def _req(url: str, key: str, method="GET", body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json", "X-Title": "Lumina"},
    )
    try:
        return json.load(urllib.request.urlopen(r, timeout=60))
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode()[:500]}")


def list_models(key: str) -> None:
    data = _req(f"{BASE}/models", key)
    models = data.get("data", data) if isinstance(data, dict) else data
    print("Available video models:")
    for m in models if isinstance(models, list) else []:
        mid = m.get("id") or m.get("slug") if isinstance(m, dict) else m
        print(" -", mid)
    if not models:
        print(json.dumps(data, indent=2)[:800])


def generate(prompt: str, key: str, model: str) -> None:
    print(f"model: {model}\nprompt: {prompt}\nsubmitting...")
    job = _req(BASE, key, "POST", {"model": model, "prompt": prompt})
    job_id = job["id"]
    print("job id:", job_id, "- polling (up to ~5 min)...")

    deadline = time.time() + 300
    while time.time() < deadline:
        st = _req(f"{BASE}/{job_id}", key)
        status = (st.get("status") or "").lower()
        print("  status:", status)
        if status == "completed":
            urls = st.get("unsigned_urls") or []
            if not urls:
                sys.exit(f"completed but no unsigned_urls. raw: {json.dumps(st)[:500]}")
            out = Path(__file__).resolve().parent.parent / "out.mp4"
            r = urllib.request.Request(urls[0], headers={"Authorization": f"Bearer {key}"})
            out.write_bytes(urllib.request.urlopen(r, timeout=120).read())
            print(f"OK — saved video to {out}")
            print("usage:", st.get("usage"))
            return
        if status in ("failed", "cancelled", "canceled", "expired"):
            sys.exit(f"terminal status {status}: {st.get('error')}")
        time.sleep(6)
    sys.exit("timed out after 5 minutes")


def main() -> None:
    key, model = _load()
    args = sys.argv[1:]
    if "--list" in args:
        list_models(key)
        return
    if "--model" in args:
        i = args.index("--model")
        model = args[i + 1]
        args = args[:i] + args[i + 2:]
    prompt = args[0] if args else "a lonely lighthouse at dusk, cinematic, slow push in"
    generate(prompt, key, model)


if __name__ == "__main__":
    main()
