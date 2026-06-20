from __future__ import annotations

from dataclasses import asdict
from typing import Any

import retail_price_tracker_mcp.adapters as adapters_pkg
from retail_price_tracker_mcp.db import TrackerDB
from retail_price_tracker_mcp.models import CheckResult, Product
from retail_price_tracker_mcp.service import TrackerService


class StubAdapter:
    """Adapter returning scripted CheckResults so we can drive event logic."""

    name = "stub_store"

    def __init__(self, results: list[CheckResult]):
        self._results = list(results)

    def supports(self, url: str) -> bool:
        return url.startswith("stub://")

    def check(self, product: Product) -> CheckResult:
        result = self._results.pop(0)
        return CheckResult(**{**asdict(result), "product_id": product.id or 0, "url": product.url})

    def resolve(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        return []


def _result(
    price: int | None = None,
    stock: str = "Y",
    sale_label: str | None = None,
    events: list[dict[str, Any]] | None = None,
) -> CheckResult:
    return CheckResult(
        product_id=0,
        name="Demo",
        url="stub://demo",
        adapter="stub_store",
        current_price=price,
        stock_status=stock,
        sale_label=sale_label,
        events=list(events or []),
    )


def _service(tmp_path, results, monkeypatch) -> TrackerService:
    monkeypatch.setattr(adapters_pkg, "ADAPTERS", [StubAdapter(results)])
    return TrackerService(TrackerDB(tmp_path / "tracker.db"))


def _event_types(check: dict[str, Any]) -> list[str]:
    return [event["event_type"] for event in check["events"]]


def test_is_in_stock_classification():
    from retail_price_tracker_mcp.models import is_in_stock

    assert is_in_stock("Y")
    assert is_in_stock("yes")
    assert is_in_stock("IN_STOCK")
    assert not is_in_stock("N")
    assert not is_in_stock(None)
    assert not is_in_stock("")


def test_check_emits_price_drop_when_price_falls(tmp_path, monkeypatch):
    service = _service(tmp_path, [_result(price=590), _result(price=390)], monkeypatch)
    product = service.add_product("stub://demo")
    service.check_product(product["id"])
    second = service.check_product(product["id"])
    assert "price_drop" in _event_types(second)


def test_check_skips_price_drop_when_price_unchanged(tmp_path, monkeypatch):
    service = _service(tmp_path, [_result(price=590), _result(price=590)], monkeypatch)
    product = service.add_product("stub://demo")
    service.check_product(product["id"])
    second = service.check_product(product["id"])
    assert "price_drop" not in _event_types(second)


def test_check_emits_below_target_at_or_under_target(tmp_path, monkeypatch):
    service = _service(tmp_path, [_result(price=390)], monkeypatch)
    product = service.add_product("stub://demo", target_price=390)
    first = service.check_product(product["id"])
    assert "below_target" in _event_types(first)


def test_check_emits_restock_when_stock_returns(tmp_path, monkeypatch):
    service = _service(tmp_path, [_result(stock="N"), _result(stock="Y")], monkeypatch)
    product = service.add_product("stub://demo")
    service.check_product(product["id"])
    second = service.check_product(product["id"])
    assert "restock" in _event_types(second)


def test_check_skips_restock_on_first_check(tmp_path, monkeypatch):
    service = _service(tmp_path, [_result(stock="Y")], monkeypatch)
    product = service.add_product("stub://demo")
    first = service.check_product(product["id"])
    assert "restock" not in _event_types(first)


def test_check_skips_restock_when_still_in_stock(tmp_path, monkeypatch):
    service = _service(tmp_path, [_result(stock="Y"), _result(stock="Y")], monkeypatch)
    product = service.add_product("stub://demo")
    service.check_product(product["id"])
    second = service.check_product(product["id"])
    assert "restock" not in _event_types(second)


def test_sale_event_suppressed_when_notify_on_sale_false(tmp_path, monkeypatch):
    sale = {"event_type": "sale_label", "label": "sale"}
    service = _service(tmp_path, [_result(sale_label="sale", events=[sale])], monkeypatch)
    product = service.add_product("stub://demo", notify_on_sale=False)
    first = service.check_product(product["id"])
    assert "sale_label" not in _event_types(first)


def test_sale_event_kept_when_notify_on_sale_true(tmp_path, monkeypatch):
    sale = {"event_type": "sale_label", "label": "sale"}
    service = _service(tmp_path, [_result(sale_label="sale", events=[sale])], monkeypatch)
    product = service.add_product("stub://demo", notify_on_sale=True)
    first = service.check_product(product["id"])
    assert "sale_label" in _event_types(first)
