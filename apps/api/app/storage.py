"""Object-storage helpers. Copies provider outputs into our own bucket so we
don't hot-link expiring provider URLs (Architecture section 3.6)."""
from __future__ import annotations

import httpx

from app.config import get_settings


def _client():
    # Imported lazily so the module loads even if boto3 isn't installed yet.
    import boto3

    s = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=s.s3_endpoint_url,
        aws_access_key_id=s.s3_access_key,
        aws_secret_access_key=s.s3_secret_key,
        region_name=s.s3_region,
    )


async def ingest_url(src_url: str, key: str, content_type: str) -> str:
    """Store an asset under `key` and return its public URL.

    Handles both remote http(s) URLs (fal/Replicate) and inline base64 `data:`
    URLs (OpenRouter image output)."""
    s = get_settings()
    if src_url.startswith("data:"):
        body, ct = _decode_data_url(src_url)
        content_type = ct or content_type
    else:
        headers = {}
        # OpenRouter's unsigned_urls point back at its API and need the token.
        if "openrouter.ai" in src_url:
            headers["Authorization"] = f"Bearer {s.openrouter_api_key}"
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as http:
            resp = await http.get(src_url, headers=headers)
            resp.raise_for_status()
            body = resp.content

    _client().put_object(Bucket=s.s3_bucket, Key=key, Body=body, ContentType=content_type)
    return f"{s.s3_public_base_url}/{key}"


def _decode_data_url(data_url: str) -> tuple[bytes, str | None]:
    """Parse `data:[<mediatype>][;base64],<data>` into (bytes, content_type)."""
    import base64

    header, _, payload = data_url[len("data:"):].partition(",")
    content_type = header.split(";")[0] or None
    if ";base64" in header:
        return base64.b64decode(payload), content_type
    from urllib.parse import unquote_to_bytes

    return unquote_to_bytes(payload), content_type
