"""The provider-agnostic interface every adapter implements.

Keeping every provider behind this contract is what lets the rest of the system
stay vendor-neutral and lets the router fail over between equivalent models.
See docs/ARCHITECTURE.md section 3.4.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class NormalizedRequest:
    """Provider-independent description of one generation, produced by the
    preset engine from a user request."""

    capability: str            # text_to_video | image_to_video | text_to_image
    prompt: str
    image_url: str | None = None
    params: dict = field(default_factory=dict)
    model: str = ""


class ProviderState(str, enum.Enum):
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


@dataclass
class ProviderResult:
    """A single output asset returned by a provider."""

    kind: str          # video | image | audio
    url: str           # provider-hosted (usually expiring) URL
    thumbnail_url: str | None = None


@dataclass
class ProviderStatus:
    state: ProviderState
    results: list[ProviderResult] = field(default_factory=list)
    error: str | None = None


class GenerationProvider(Protocol):
    """Contract for a hosted-model adapter."""

    name: str

    def estimate_cost(self, req: NormalizedRequest) -> int:
        """Estimated provider cost in cents (for margin tracking / routing)."""
        ...

    async def submit(self, req: NormalizedRequest) -> str:
        """Kick off generation; return an opaque provider job reference."""
        ...

    async def poll(self, ref: str) -> ProviderStatus:
        """Check status of a previously submitted job."""
        ...
