"""Live smoke test for OpenRouter image generation.

Run on a network-enabled machine (the cloud sandbox blocks openrouter.ai):

    cd apps/api
    python scripts/smoke_openrouter_image.py "a lonely lighthouse at dusk"

Saves the generated image to apps/api/out.png so you can eyeball it. Stdlib only;
key + image model come from the environment or the gitignored apps/api/.env.

NOTE: image models cost money (unlike the free chat model you tested with). If
this 402s, add a little credit, or set OPENROUTER_IMAGE_MODEL to a model your
account can use.
"""
from __future__ import annotations

import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

API = "https://openrouter.ai/api/v1/chat/completions"


def _load() -> tuple[str, str]:
    key = os.environ.get("OPENROUTER_API_KEY")
    model = os.environ.get("OPENROUTER_IMAGE_MODEL", "google/gemini-2.5-flash-image-preview")
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if (not key) and env_file.exists():
        pairs = dict(re.findall(r"^(\w+)=(.*)$", env_file.read_text(), re.M))
        key = pairs.get("OPENROUTER_API_KEY")
        model = pairs.get("OPENROUTER_IMAGE_MODEL", model)
    if not key:
        sys.exit("No OPENROUTER_API_KEY in environment or apps/api/.env")
    return key.strip(), model.strip()


def main() -> None:
    prompt = sys.argv[1] if len(sys.argv) > 1 else "a lonely lighthouse at dusk, cinematic"
    key, model = _load()
    print(f"model: {model}\nprompt: {prompt}\n")

    body = json.dumps(
        {"model": model, "modalities": ["image", "text"], "messages": [{"role": "user", "content": prompt}]}
    ).encode()
    req = urllib.request.Request(
        API,
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json", "X-Title": "Lumina"},
    )
    try:
        resp = json.load(urllib.request.urlopen(req, timeout=120))
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode()[:400]}")

    images = []
    for choice in resp.get("choices", []):
        for img in (choice.get("message", {}) or {}).get("images", []) or []:
            url = (img.get("image_url") or {}).get("url")
            if url:
                images.append(url)
    if not images:
        sys.exit(f"No image in response. Raw: {json.dumps(resp)[:400]}")

    data_url = images[0]
    payload = data_url.split(",", 1)[1] if data_url.startswith("data:") else data_url
    out = Path(__file__).resolve().parent.parent / "out.png"
    out.write_bytes(base64.b64decode(payload))
    print(f"OK — saved {len(images)} image(s). First written to: {out}")
    print("usage:", resp.get("usage"))


if __name__ == "__main__":
    main()
