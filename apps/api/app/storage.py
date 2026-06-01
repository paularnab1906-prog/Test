"""Object-storage helpers.

Two backends, chosen by `storage_backend`:
  * local — write under `media_dir`, served by the API at /media/<key> (zero infra,
            great for local testing).
  * s3    — S3-compatible object storage (MinIO/R2/S3) for production.

Copies provider outputs into our own storage so we don't hot-link expiring
provider URLs (Architecture section 3.6). Handles http(s), base64 `data:` URLs
(OpenRouter images), and OpenRouter `unsigned_urls` that need bearer auth.
"""
from __future__ import annotations

from pathlib import Path

import httpx

from app.config import get_settings


async def ingest_url(src_url: str, key: str, content_type: str) -> str:
    """Store an asset under `key` and return its public URL."""
    body, ct = await _fetch_bytes(src_url)
    content_type = ct or content_type

    s = get_settings()
    if s.storage_backend == "local":
        dest = Path(s.media_dir) / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(body)
        return f"{s.api_base_url}/media/{key}"

    _s3_client().put_object(Bucket=s.s3_bucket, Key=key, Body=body, ContentType=content_type)
    return f"{s.s3_public_base_url}/{key}"


async def _fetch_bytes(src_url: str) -> tuple[bytes, str | None]:
    if src_url.startswith("data:"):
        return _decode_data_url(src_url)
    headers = {}
    # OpenRouter's unsigned_urls point back at its API and need the token.
    if "openrouter.ai" in src_url:
        headers["Authorization"] = f"Bearer {get_settings().openrouter_api_key}"
    async with httpx.AsyncClient(timeout=120, follow_redirects=True) as http:
        resp = await http.get(src_url, headers=headers)
        resp.raise_for_status()
        return resp.content, resp.headers.get("content-type")


def _decode_data_url(data_url: str) -> tuple[bytes, str | None]:
    """Parse `data:[<mediatype>][;base64],<data>` into (bytes, content_type)."""
    import base64

    header, _, payload = data_url[len("data:"):].partition(",")
    content_type = header.split(";")[0] or None
    if ";base64" in header:
        return base64.b64decode(payload), content_type
    from urllib.parse import unquote_to_bytes

    return unquote_to_bytes(payload), content_type


def _s3_client():
    import boto3

    s = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=s.s3_endpoint_url,
        aws_access_key_id=s.s3_access_key,
        aws_secret_access_key=s.s3_secret_key,
        region_name=s.s3_region,
    )
