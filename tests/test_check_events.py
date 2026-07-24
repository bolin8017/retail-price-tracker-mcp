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
    assert is_in_stock("TRUE")
    assert is_in_stock("1")
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


def test_check_skips_price_drop_when_price_rises(tmp_path, monkeypatch):
    service = _service(tmp_path, [_result(price=390), _result(price=590)], monkeypatch)
    product = service.add_product("stub://demo")
    service.check_product(product["id"])
    second = service.check_product(product["id"])
    assert "price_drop" not in _event_types(second)


def test_check_skips_below_target_when_price_above_target(tmp_path, monkeypatch):
    service = _service(tmp_path, [_result(price=400)], monkeypatch)
    product = service.add_product("stub://demo", target_price=390)
    first = service.check_product(product["id"])
    assert "below_target" not in _event_types(first)


def test_check_emits_below_target_at_or_under_target(tmp_path, monkeypatch):
    service = _service(tmp_path, [_result(price=390)], monkeypatch)
    product = service.add_product("stub://demo", target_price=390)
    first = service.check_product(product["id"])
    assert "below_target" in _event_types(first)


def test_below_target_fires_only_on_crossing(tmp_path, monkeypatch):
    # The documented cron contract is "stay silent if nothing changed"; a
    # price sitting below target must not re-notify on every check.
    service = _service(tmp_path, [_result(price=380), _result(price=380)], monkeypatch)
    product = service.add_product("stub://demo", target_price=390)
    first = service.check_product(product["id"])
    second = service.check_product(product["id"])
    assert "below_target" in _event_types(first)
    assert "below_target" not in _event_types(second)


def test_below_target_refires_after_price_recovers(tmp_path, monkeypatch):
    service = _service(
        tmp_path, [_result(price=380), _result(price=450), _result(price=380)], monkeypatch
    )
    product = service.add_product("stub://demo", target_price=390)
    assert "below_target" in _event_types(service.check_product(product["id"]))
    assert "below_target" not in _event_types(service.check_product(product["id"]))
    assert "below_target" in _event_types(service.check_product(product["id"]))


def test_stock_status_event_on_going_out_of_stock(tmp_path, monkeypatch):
    service = _service(tmp_path, [_result(stock="Y"), _result(stock="N")], monkeypatch)
    product = service.add_product("stub://demo")
    service.check_product(product["id"])
    second = service.check_product(product["id"])
    assert "stock_status" in _event_types(second)


def test_no_stock_status_event_while_still_out_of_stock(tmp_path, monkeypatch):
    service = _service(tmp_path, [_result(stock="N"), _result(stock="N")], monkeypatch)
    product = service.add_product("stub://demo")
    service.check_product(product["id"])
    second = service.check_product(product["id"])
    assert "stock_status" not in _event_types(second)


def test_generic_static_below_target_not_duplicated_or_respammed(tmp_path, monkeypatch):
    # generic_static echoes the stored price, so a steady below-target state
    # must produce zero below_target events (no adapter/service double-emit,
    # no level-triggered re-fire).
    from retail_price_tracker_mcp.adapters.generic import GenericStaticAdapter

    monkeypatch.setattr(adapters_pkg, "ADAPTERS", [GenericStaticAdapter()])
    service = TrackerService(TrackerDB(tmp_path / "tracker.db"))
    product = service.add_product("static://demo", target_price=500)
    service.db.record_check(
        CheckResult(
            product_id=product["id"],
            name="Demo",
            url="static://demo",
            adapter="generic_static",
            current_price=400,
        )
    )
    check = service.check_product(product["id"])
    assert _event_types(check).count("below_target") == 0


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


def test_no_price_check_keeps_stored_price_and_price_drop_detection(tmp_path, monkeypatch):
    # A check that learned no price must not erase the stored baseline.
    service = _service(
        tmp_path, [_result(price=590), _result(price=None), _result(price=390)], monkeypatch
    )
    product = service.add_product("stub://demo")
    service.check_product(product["id"])
    service.check_product(product["id"])  # learned nothing
    stored = service.db.get_product(product["id"])
    assert stored is not None and stored.current_price == 590
    third = service.check_product(product["id"])
    assert "price_drop" in _event_types(third)


def test_restock_survives_intervening_failed_check(tmp_path, monkeypatch):
    service = _service(
        tmp_path,
        [_result(stock="N"), _result(price=None, stock=None), _result(stock="Y")],
        monkeypatch,
    )
    product = service.add_product("stub://demo")
    service.check_product(product["id"])
    service.check_product(product["id"])  # failed observation, no stock info
    third = service.check_product(product["id"])
    assert "restock" in _event_types(third)


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
