from __future__ import annotations

from retail_price_tracker_mcp.models import CheckResult, Product


class GenericStaticAdapter:
    """Test/demo adapter that records a product without doing network I/O."""

    name = "generic_static"

    def supports(self, url: str) -> bool:
        return url.startswith("static://") or url.startswith("test://")

    def check(self, product: Product) -> CheckResult:
        events = []
        if (
            product.current_price is not None
            and product.target_price is not None
            and product.current_price <= product.target_price
        ):
            events.append(
                {
                    "event_type": "below_target",
                    "message": "Current static price is at or below target.",
                }
            )
        return CheckResult(
            product_id=product.id or 0,
            name=product.name,
            url=product.url,
            adapter=self.name,
            current_price=product.current_price,
            currency=product.currency,
            events=events,
            raw={"source": "generic_static"},
        )
