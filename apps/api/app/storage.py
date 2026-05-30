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
    """Download a remote asset and store it under `key`; return the public URL."""
    s = get_settings()
    async with httpx.AsyncClient(timeout=60) as http:
        resp = await http.get(src_url)
        resp.raise_for_status()
        body = resp.content

    _client().put_object(Bucket=s.s3_bucket, Key=key, Body=body, ContentType=content_type)
    return f"{s.s3_public_base_url}/{key}"
