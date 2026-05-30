"""Unit tests for the preset engine — no DB or network needed."""
from app import presets


def test_presets_load():
    all_presets = presets.list_presets()
    ids = {p["id"] for p in all_presets}
    assert "crash_zoom" in ids
    assert "dolly_orbit" in ids


def test_build_request_applies_suffix_and_model():
    preset = presets.get_preset("crash_zoom")
    req = presets.build_request(
        preset,
        prompt="a fox in a neon city",
        image_url="https://example.com/fox.jpg",
        overrides={"duration_s": 8, "not_allowed": "x"},
    )
    assert req.capability == "image_to_video"
    assert req.model == "kling-video/v1.6/pro"
    assert "crash zoom" in req.prompt
    # allowed override applied, disallowed override dropped
    assert req.params["duration_s"] == 8
    assert "not_allowed" not in req.params


def test_provider_for():
    assert presets.provider_for(presets.get_preset("crash_zoom")) == "fal"
