from __future__ import annotations

from .base import StoreAdapter
from .generic import GenericStaticAdapter
from .uniqlo_tw import UniqloTwAdapter

ADAPTERS: list[StoreAdapter] = [UniqloTwAdapter(), GenericStaticAdapter()]


def choose_adapter(url: str) -> StoreAdapter:
    for adapter in ADAPTERS:
        if adapter.supports(url):
            return adapter
    raise ValueError(f"No adapter supports URL: {url}")


def get_adapter(name: str) -> StoreAdapter:
    for adapter in ADAPTERS:
        if adapter.name == name:
            return adapter
    raise ValueError(f"Unknown adapter: {name}")
