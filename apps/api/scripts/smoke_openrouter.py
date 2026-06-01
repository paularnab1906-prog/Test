"""Live smoke test for the Prompt Director against OpenRouter.

Run this on a machine with network access (the cloud sandbox blocks openrouter.ai):

    cd apps/api
    python scripts/smoke_openrouter.py "a lonely lighthouse"

Key is read from the environment or apps/api/.env (gitignored). Stdlib only.

It first does a tiny "ping" to isolate account/key problems from payload problems,
retries transient 5xx errors, and prints OpenRouter's request id on failure.
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

API = "https://openrouter.ai/api/v1/chat/completions"


def _load_key() -> tuple[str, str]:
    key = os.environ.get("OPENROUTER_API_KEY")
    model = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if (not key) and env_file.exists():
        pairs = dict(re.findall(r"^(\w+)=(.*)$", env_file.read_text(), re.M))
        key = pairs.get("OPENROUTER_API_KEY")
        model = pairs.get("OPENROUTER_MODEL", model)
    if not key:
        sys.exit("No OPENROUTER_API_KEY in environment or apps/api/.env")
    return key.strip(), model.strip()


def _system_prompt() -> str:
    src = (Path(__file__).resolve().parent.parent / "app/llm/director.py").read_text()
    return src.split('_SYSTEM = """', 1)[1].split('"""', 1)[0]


def call(messages: list[dict], model: str, key: str, max_tokens: int = 320) -> dict:
    """POST with up to 3 retries on transient 5xx. Raises on final failure."""
    body = json.dumps({"model": model, "messages": messages, "max_tokens": max_tokens}).encode()
    last_err = None
    for attempt in range(1, 4):
        req = urllib.request.Request(
            API,
            data=body,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://lumina.local",
                "X-Title": "Lumina",
            },
        )
        try:
            return json.load(urllib.request.urlopen(req, timeout=40))
        except urllib.error.HTTPError as e:
            detail = e.read().decode()[:400]
            rid = e.headers.get("x-request-id", "?")
            last_err = f"HTTP {e.code} (request-id {rid}): {detail}"
            if 500 <= e.code < 600 and attempt < 3:
                print(f"  attempt {attempt} got {e.code}, retrying...")
                time.sleep(2 * attempt)
                continue
            break
        except Exception as e:  # noqa: BLE001
            last_err = f"{type(e).__name__}: {e}"
            break
    raise SystemExit(last_err)


def main() -> None:
    idea = sys.argv[1] if len(sys.argv) > 1 else "a lonely lighthouse"
    key, model = _load_key()
    print(f"key: ...{key[-6:]}   model: {model}\n")

    print("[1/2] account ping (minimal request)...")
    ping = call([{"role": "user", "content": "Reply with the single word: ok"}], model, key, 5)
    print("      ->", ping["choices"][0]["message"]["content"].strip())
    print("      account + key + model all good.\n")

    print("[2/2] full Prompt Director call...")
    messages = [
        {"role": "system", "content": _system_prompt()},
        {"role": "user", "content": f"Idea (capability=image_to_video, style=camera-motion): {idea}"},
    ]
    resp = call(messages, model, key)
    print("\ninput :", idea)
    print("output:", resp["choices"][0]["message"]["content"].strip())
    print("usage :", resp.get("usage"))


if __name__ == "__main__":
    main()
