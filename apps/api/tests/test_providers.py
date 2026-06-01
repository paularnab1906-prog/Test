"""Provider input-mapping and output-parsing tests (pure, no network)."""
from app.providers import fal, replicate
from app.providers.base import NormalizedRequest


def _img():
    return NormalizedRequest(
        capability="text_to_image",
        prompt="a fox",
        params={"aspect_ratio": "3:4", "num_images": 2},
        model="fal-ai/flux/dev",
    )


def _vid():
    return NormalizedRequest(
        capability="text_to_video",
        prompt="epic mountains",
        params={"duration_s": 5, "aspect_ratio": "16:9"},
        model="fal-ai/kling-video/v1.6/pro/text-to-video",
    )


def test_fal_image_input_maps_aspect_ratio():
    body = fal._fal_input(_img())
    assert body["image_size"] == "portrait_4_3"
    assert body["num_images"] == 2


def test_fal_video_input_omits_image_when_absent():
    body = fal._fal_input(_vid())
    assert "image_url" not in body
    assert body["duration"] == "5"


def test_fal_output_parsing():
    assert fal._parse_fal_output({"video": {"url": "u"}})[0].kind == "video"
    assert fal._parse_fal_output({"images": [{"url": "u"}]})[0].kind == "image"
    assert fal._parse_fal_output({}) == []


def test_replicate_output_parsing_handles_str_and_list():
    assert replicate._parse_replicate_output("u", "video")[0].url == "u"
    assert len(replicate._parse_replicate_output(["a", "b"], "image")) == 2
    assert replicate._parse_replicate_output(None, "image") == []


def test_openrouter_video_output_parsing():
    from app.providers import openrouter_video as ov

    res = ov._parse_video_output({"unsigned_urls": ["https://openrouter.ai/x", "y"]})
    assert len(res) == 2 and res[0].kind == "video"
    assert ov._parse_video_output({}) == []


def test_byteplus_output_parsing():
    from app.providers import byteplus as bp

    ok = bp._parse_output({"status": "succeeded", "content": {"video_url": "https://x/v.mp4"}})
    assert len(ok) == 1 and ok[0].kind == "video"
    assert bp._parse_output({"content": {}}) == []
    assert bp._parse_output({}) == []


def test_openrouter_image_output_parsing():
    from app.providers import openrouter_image as oi

    resp = {"choices": [{"message": {"images": [{"image_url": {"url": "data:image/png;base64,AA"}}]}}]}
    res = oi._parse_image_output(resp)
    assert len(res) == 1 and res[0].kind == "image"
    assert oi._parse_image_output({"choices": [{"message": {}}]}) == []
