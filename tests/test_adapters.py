from __future__ import annotations

from typing import Any

import httpx

from retail_price_tracker_mcp.adapters.uniqlo_tw import (
    UniqloTwAdapter,
    _candidate_from_product,
    _search_query_for_code,
)
from retail_price_tracker_mcp.models import Product


class FakeResponse:
    def __init__(self, payload: dict[str, Any], status_code: int = 200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "bad status",
                request=httpx.Request("POST", "https://example.test"),
                response=httpx.Response(self.status_code),
            )

    def json(self) -> dict[str, Any]:
        return self.payload


def test_uniqlo_tw_supports_product_url():
    adapter = UniqloTwAdapter()
    url = "https://www.uniqlo.com/tw/zh_TW/products/E471234-000"
    assert adapter.supports(url)
    assert adapter.parse_product_code(url) == "E471234-000"


def test_uniqlo_tw_supports_product_code_query():
    adapter = UniqloTwAdapter()
    url = "https://www.uniqlo.com/tw/zh_TW/product-detail.html?productCode=u0000000053128"
    assert adapter.supports(url)
    assert adapter.parse_product_code(url) == "u0000000053128"


def test_uniqlo_tw_fetches_price_from_search_api(monkeypatch):
    def fake_post(*args: Any, **kwargs: Any) -> FakeResponse:
        assert kwargs["json"]["description"] == "475355"
        return FakeResponse(
            {
                "success": True,
                "resp": [
                    {
                        "productList": [
                            {
                                "productCode": "u0000000053128",
                                "productName": "AIRism棉質寬版圓領T恤 475355",
                                "shortName": "AIRism棉質寬版圓領T恤",
                                "minPrice": 390,
                                "originPrice": 590,
                                "priceColor": "red",
                                "stock": "Y",
                                "pubSuffix": "000",
                            }
                        ]
                    }
                ],
            }
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    adapter = UniqloTwAdapter()
    product = Product(
        id=1,
        url="https://www.uniqlo.com/tw/zh_TW/products/E475355-000",
        adapter=adapter.name,
        target_price=390,
    )
    result = adapter.check(product)
    assert result.current_price == 390
    assert result.name == "AIRism棉質寬版圓領T恤"
    assert result.sale_label == "sale"
    assert result.raw["origin_price"] == 590


def test_uniqlo_tw_does_not_fabricate_price_when_no_match(monkeypatch):
    def fake_post(*args: Any, **kwargs: Any) -> FakeResponse:
        return FakeResponse({"success": True, "resp": [{"productList": []}]})

    monkeypatch.setattr(httpx, "post", fake_post)
    adapter = UniqloTwAdapter()
    product = Product(
        id=1,
        url="https://www.uniqlo.com/tw/zh_TW/products/E471234-000",
        adapter=adapter.name,
    )
    result = adapter.check(product)
    assert result.current_price is None
    assert result.events[0]["event_type"] == "unsupported_live_fetch"


def test_candidate_url_is_checkable_via_style_code():
    # resolve() must build a URL that check_product can re-fetch: it has to carry
    # the searchable 6-digit style code, not the internal `productCode` (u...),
    # which the description-search API cannot look up.
    product = {
        "productCode": "u0000000054386",
        "code": "486091",
        "pubSuffix": "000",
        "productName": "女裝 棉質舒適九分褲 486091",
        "shortName": "棉質舒適九分褲",
        "minPrice": 790,
        "originPrice": 790,
        "stock": "Y",
    }
    candidate = _candidate_from_product(product)
    assert candidate["url"] == "https://www.uniqlo.com/tw/zh_TW/products/E486091-000"
    code = UniqloTwAdapter().parse_product_code(candidate["url"])
    assert _search_query_for_code(code) == "486091"


def test_uniqlo_tw_resolves_product_candidates(monkeypatch):
    def fake_post(*args: Any, **kwargs: Any) -> FakeResponse:
        assert kwargs["json"]["description"] == "AIRism"
        assert kwargs["json"]["pageSize"] == 5
        return FakeResponse(
            {
                "success": True,
                "resp": [
                    {
                        "productList": [
                            {
                                "productCode": "u0000000053128",
                                "productName": "AIRism棉質寬版圓領T恤 475355",
                                "shortName": "AIRism棉質寬版圓領T恤",
                                "minPrice": 590,
                                "originPrice": 590,
                                "priceColor": "black",
                                "stock": "Y",
                                "pubSuffix": "000",
                                "defaultColor": "COL07",
                            }
                        ]
                    }
                ],
            }
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    candidates = UniqloTwAdapter().resolve("AIRism", limit=5)
    assert candidates == [
        {
            "adapter": "uniqlo_tw",
            "product_code": "u0000000053128",
            "name": "AIRism棉質寬版圓領T恤",
            "url": "https://www.uniqlo.com/tw/zh_TW/products/E475355-000",
            "current_price": 590,
            "origin_price": 590,
            "currency": "TWD",
            "sale_label": None,
            "stock_status": "Y",
            "raw": {
                "price_color": "black",
                "pub_suffix": "000",
                "default_color": "COL07",
            },
        }
    ]
