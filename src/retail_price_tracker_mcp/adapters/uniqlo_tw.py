from __future__ import annotations

import re
from urllib.parse import urlparse

from retail_price_tracker_mcp.models import CheckResult, Product

UNIQLO_TW_HOSTS = {"www.uniqlo.com", "uniqlo.com"}
PRODUCT_RE = re.compile(r"/(?:tw/)?(?:zh_TW/)?products/(?P<code>[A-Za-z0-9_-]+)")


class UniqloTwAdapter:
    name = "uniqlo_tw"

    def supports(self, url: str) -> bool:
        parsed = urlparse(url)
        return (
            parsed.netloc in UNIQLO_TW_HOSTS
            and "/tw/" in parsed.path
            and "/products/" in parsed.path
        )

    def parse_product_code(self, url: str) -> str | None:
        match = PRODUCT_RE.search(urlparse(url).path)
        return match.group("code") if match else None

    def check(self, product: Product) -> CheckResult:
        code = self.parse_product_code(product.url)
        return CheckResult(
            product_id=product.id or 0,
            name=product.name,
            url=product.url,
            adapter=self.name,
            current_price=product.current_price,
            currency=product.currency,
            events=[
                {
                    "event_type": "unsupported_live_fetch",
                    "message": (
                        "UNIQLO Taiwan live price fetching is not implemented yet. "
                        "The adapter parsed the URL but refuses to fabricate price data."
                    ),
                }
            ],
            raw={"product_code": code, "live_fetch": "not_implemented"},
        )
