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


def test_re_add_preserves_existing_config(tmp_path):
    # Re-adding a tracked URL (idempotent re-track) must not silently reset
    # the user's alert configuration.
    service = TrackerService(TrackerDB(tmp_path / "tracker.db"))
    service.add_product(
        "static://demo", target_price=390, notify_on_sale=False, sizes=["M"], name="Demo"
    )
    again = service.add_product("static://demo")
    assert again["target_price"] == 390
    assert again["notify_on_sale"] is False
    assert again["sizes"] == ["M"]
    assert again["name"] == "Demo"


def test_re_add_overrides_only_provided_fields(tmp_path):
    service = TrackerService(TrackerDB(tmp_path / "tracker.db"))
    service.add_product("static://demo", target_price=390, notify_on_sale=False, sizes=["M"])
    again = service.add_product("static://demo", target_price=350, sizes=["L"])
    assert again["target_price"] == 350
    assert again["sizes"] == ["L"]
    assert again["notify_on_sale"] is False


def test_remove_product(tmp_path):
    service = TrackerService(TrackerDB(tmp_path / "tracker.db"))
    product = service.add_product("static://demo")
    removed = service.remove_product(product["id"])
    assert removed == {"product_id": product["id"], "removed": True}
    assert service.list_products()["products"] == []


def test_price_history_respects_days_window(tmp_path):
    from datetime import UTC, datetime, timedelta

    from retail_price_tracker_mcp.models import CheckResult

    service = TrackerService(TrackerDB(tmp_path / "tracker.db"))
    product = service.add_product("static://demo")

    def record(price: int, days_ago: int) -> None:
        checked_at = (
            (datetime.now(UTC) - timedelta(days=days_ago)).replace(microsecond=0).isoformat()
        )
        service.db.record_check(
            CheckResult(
                product_id=product["id"],
                name="Demo",
                url="static://demo",
                adapter="generic_static",
                current_price=price,
                checked_at=checked_at,
            )
        )

    record(500, days_ago=200)  # outside the window
    record(400, days_ago=10)  # inside
    result = service.price_history(product["id"], days=90)
    assert [item["price"] for item in result["history"]] == [400]


def test_price_history_is_not_capped_at_200_rows(tmp_path):
    from datetime import UTC, datetime, timedelta

    from retail_price_tracker_mcp.models import CheckResult

    service = TrackerService(TrackerDB(tmp_path / "tracker.db"))
    product = service.add_product("static://demo")
    base = datetime.now(UTC).replace(microsecond=0) - timedelta(days=1)
    for i in range(250):
        service.db.record_check(
            CheckResult(
                product_id=product["id"],
                name="Demo",
                url="static://demo",
                adapter="generic_static",
                current_price=100 + i,
                checked_at=(base + timedelta(minutes=i)).isoformat(),
            )
        )
    result = service.price_history(product["id"], days=90)
    assert len(result["history"]) == 250


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
