"""Live smoke test for the Prompt Director against OpenRouter.

Run this on a machine with network access (this sandbox blocks openrouter.ai):

    cd apps/api
    # key comes from the environment or apps/api/.env (gitignored)
    python scripts/smoke_openrouter.py "a lonely lighthouse"

Uses only the stdlib so it works without installing the app deps. It mirrors the
director's real system prompt so you can eyeball output quality before tuning.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path


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
    return key, model


def _system_prompt() -> str:
    # Reuse the exact SYSTEM string the app uses, so this reflects real behavior.
    src = (Path(__file__).resolve().parent.parent / "app/llm/director.py").read_text()
    return src.split('_SYSTEM = """', 1)[1].split('"""', 1)[0]


def main() -> None:
    idea = sys.argv[1] if len(sys.argv) > 1 else "a lonely lighthouse"
    key, model = _load_key()
    messages = [
        {"role": "system", "content": _system_prompt()},
        {"role": "user", "content": f"Idea (capability=image_to_video, style=camera-motion): {idea}"},
    ]
    body = json.dumps({"model": model, "messages": messages, "max_tokens": 320}).encode()
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "X-Title": "Lumina",
        },
    )
    try:
        resp = json.load(urllib.request.urlopen(req, timeout=40))
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode()[:400]}")
    print("model :", resp.get("model"))
    print("input :", idea)
    print("output:", resp["choices"][0]["message"]["content"].strip())
    print("usage :", resp.get("usage"))


if __name__ == "__main__":
    main()
