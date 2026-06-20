from typing import Any

import retail_price_tracker_mcp.service as service_module
from retail_price_tracker_mcp.db import TrackerDB
from retail_price_tracker_mcp.service import TrackerService


def test_service_add_list_check_all(tmp_path):
    service = TrackerService(TrackerDB(tmp_path / "tracker.db"))
    product = service.add_product("static://demo", target_price=390, name="Demo")
    assert product["name"] == "Demo"
    listed = service.list_products()
    assert len(listed["products"]) == 1
    result = service.check_all()
    assert result["checked"] == 1
    assert result["errors"] == []


def test_remove_product(tmp_path):
    service = TrackerService(TrackerDB(tmp_path / "tracker.db"))
    product = service.add_product("static://demo")
    removed = service.remove_product(product["id"])
    assert removed == {"product_id": product["id"], "removed": True}
    assert service.list_products()["products"] == []


def test_resolve_product_searches_adapters(monkeypatch, tmp_path):
    class FakeAdapter:
        name = "fake_store"

        def supports(self, url: str) -> bool:
            return False

        def check(self, product: Any) -> Any:
            raise AssertionError("not used")

        def resolve(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
            assert query == "AIRism"
            assert limit == 2
            return [
                {
                    "adapter": self.name,
                    "product_code": "demo-1",
                    "name": "Demo product",
                    "url": "static://demo-1",
                    "current_price": 590,
                    "origin_price": 790,
                    "currency": "TWD",
                    "sale_label": "sale",
                    "stock_status": "Y",
                    "raw": {},
                }
            ]

    monkeypatch.setattr(service_module, "ADAPTERS", [FakeAdapter()])
    service = TrackerService(TrackerDB(tmp_path / "tracker.db"))
    result = service.resolve_product("AIRism", limit=2)
    assert result == {
        "query": "AIRism",
        "candidates": [
            {
                "adapter": "fake_store",
                "product_code": "demo-1",
                "name": "Demo product",
                "url": "static://demo-1",
                "current_price": 590,
                "origin_price": 790,
                "currency": "TWD",
                "sale_label": "sale",
                "stock_status": "Y",
                "raw": {},
            }
        ],
        "errors": [],
    }
