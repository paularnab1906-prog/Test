"""Provider adapter layer — uniform interface over hosted model APIs."""
from __future__ import annotations

from app.providers.base import (
    GenerationProvider,
    NormalizedRequest,
    ProviderResult,
    ProviderStatus,
)
from app.providers.fal import FalAdapter
from app.providers.replicate import ReplicateAdapter

# Registry: provider name -> adapter instance. Router selects from here.
_REGISTRY: dict[str, GenerationProvider] = {
    "fal": FalAdapter(),
    "replicate": ReplicateAdapter(),
}


def get_provider(name: str) -> GenerationProvider:
    if name not in _REGISTRY:
        raise KeyError(f"unknown provider: {name}")
    return _REGISTRY[name]


__all__ = [
    "GenerationProvider",
    "NormalizedRequest",
    "ProviderResult",
    "ProviderStatus",
    "get_provider",
]
