from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from typing import Any

from .adapters import ADAPTERS, choose_adapter, get_adapter
from .db import TrackerDB
from .models import Product, is_in_stock


class TrackerService:
    def __init__(self, db: TrackerDB):
        self.db = db

    def add_product(
        self,
        url: str,
        target_price: int | None = None,
        notify_on_sale: bool = True,
        sizes: list[str] | None = None,
        name: str | None = None,
    ) -> dict[str, Any]:
        adapter = choose_adapter(url)
        product = Product(
            id=None,
            url=url,
            adapter=adapter.name,
            name=name,
            target_price=target_price,
            notify_on_sale=notify_on_sale,
            sizes=sizes or [],
        )
        saved = self.db.add_product(product)
        return self._product_to_dict(saved)

    def list_products(self, active_only: bool = True) -> dict[str, Any]:
        return {"products": [self._product_to_dict(p) for p in self.db.list_products(active_only)]}

    def check_product(self, product_id: int) -> dict[str, Any]:
        product = self.db.get_product(product_id)
        if product is None:
            raise ValueError(f"Product not found: {product_id}")
        adapter = get_adapter(product.adapter)
        # Read the last recorded check before this one is persisted, so we can
        # detect transitions such as a restock.
        previous = self.db.history(product_id, limit=1)
        previous_stock = previous[0]["stock_status"] if previous else None
        result = adapter.check(product)
        events = list(result.events)
        if (
            product.current_price is not None
            and result.current_price is not None
            and result.current_price < product.current_price
        ):
            events.append({"event_type": "price_drop"})
        if (
            product.target_price is not None
            and result.current_price is not None
            and result.current_price <= product.target_price
        ):
            events.append({"event_type": "below_target"})
        if (
            previous_stock is not None
            and not is_in_stock(previous_stock)
            and is_in_stock(result.stock_status)
        ):
            events.append({"event_type": "restock"})
        if not product.notify_on_sale:
            events = [event for event in events if event.get("event_type") != "sale_label"]
        result = type(result)(**{**asdict(result), "events": events})
        self.db.record_check(result)
        return asdict(result)

    def check_all(self) -> dict[str, Any]:
        checked = 0
        results = []
        errors = []
        for product in self.db.list_products(active_only=True):
            checked += 1
            try:
                results.append(self.check_product(product.id or 0))
            except Exception as exc:  # noqa: BLE001 - surface per-product errors to MCP caller
                errors.append({"product_id": product.id, "error": str(exc)})
        events = [event for result in results for event in result.get("events", [])]
        return {"checked": checked, "results": results, "events": events, "errors": errors}

    def price_history(self, product_id: int, days: int = 90) -> dict[str, Any]:
        cutoff = datetime.now(UTC) - timedelta(days=days)
        history = []
        for item in self.db.history(product_id):
            checked_at = datetime.fromisoformat(item["checked_at"])
            if checked_at >= cutoff:
                history.append(item)
        return {"product_id": product_id, "days": days, "history": history}

    def remove_product(self, product_id: int) -> dict[str, Any]:
        removed = self.db.deactivate_product(product_id)
        return {"product_id": product_id, "removed": removed}

    def resolve_product(self, query: str, limit: int = 5) -> dict[str, Any]:
        candidates: list[dict[str, Any]] = []
        errors: list[dict[str, str]] = []
        for adapter in ADAPTERS:
            try:
                candidates.extend(adapter.resolve(query, limit=limit))
            except Exception as exc:  # noqa: BLE001 - expose adapter lookup failures to callers
                errors.append({"adapter": adapter.name, "error": str(exc)})
        return {"query": query, "candidates": candidates[:limit], "errors": errors}

    @staticmethod
    def _product_to_dict(product: Product) -> dict[str, Any]:
        return asdict(product)
