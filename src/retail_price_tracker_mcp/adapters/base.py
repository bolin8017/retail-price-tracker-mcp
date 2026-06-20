from __future__ import annotations

from typing import Any, Protocol

from retail_price_tracker_mcp.models import CheckResult, Product


class StoreAdapter(Protocol):
    name: str

    def supports(self, url: str) -> bool: ...

    def check(self, product: Product) -> CheckResult: ...

    def resolve(self, query: str, limit: int = 5) -> list[dict[str, Any]]: ...
