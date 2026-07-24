from __future__ import annotations

from typing import Any

from retail_price_tracker_mcp.models import CheckResult, Product


class GenericStaticAdapter:
    """Test/demo adapter that records a product without doing network I/O."""

    name = "generic_static"

    def supports(self, url: str) -> bool:
        return url.startswith("static://") or url.startswith("test://")

    def check(self, product: Product) -> CheckResult:
        # Event derivation (below_target etc.) is the service's job; an
        # adapter emitting its own copy double-reports the same state.
        return CheckResult(
            product_id=product.id or 0,
            name=product.name,
            url=product.url,
            adapter=self.name,
            current_price=product.current_price,
            currency=product.currency,
            raw={"source": "generic_static"},
        )

    def resolve(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        return []
