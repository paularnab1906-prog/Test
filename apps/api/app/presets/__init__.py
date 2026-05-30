"""Preset / effects engine — declarative camera-motion presets.

A preset is config (YAML), not code. It maps a user request onto a concrete
(provider, model, params) NormalizedRequest. See docs/ARCHITECTURE.md section 3.5.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from app.providers.base import NormalizedRequest

_PRESET_DIR = Path(__file__).parent / "data"


def _load_all() -> dict[str, dict]:
    presets: dict[str, dict] = {}
    for path in _PRESET_DIR.glob("*.yaml"):
        data = yaml.safe_load(path.read_text())
        presets[data["id"]] = data
    return presets


_PRESETS = _load_all()


def list_presets() -> list[dict]:
    return list(_PRESETS.values())


def get_preset(preset_id: str) -> dict | None:
    return _PRESETS.get(preset_id)


def build_request(preset: dict, prompt: str, image_url: str | None, overrides: dict) -> NormalizedRequest:
    """Merge preset defaults + validated user overrides into a NormalizedRequest."""
    target = preset["target"]["primary"]
    params = dict(preset.get("defaults", {}))
    params.update(preset.get("params", {}))
    # Only allow overrides the preset explicitly opts into.
    allowed = set(preset.get("allow_override", []))
    params.update({k: v for k, v in overrides.items() if k in allowed})

    suffix = preset.get("prompt_suffix", "")
    full_prompt = f"{prompt}{suffix}"

    return NormalizedRequest(
        capability=preset["capability"],
        prompt=full_prompt,
        image_url=image_url,
        params=params,
        model=target["model"],
    )


def provider_for(preset: dict) -> str:
    return preset["target"]["primary"]["provider"]
