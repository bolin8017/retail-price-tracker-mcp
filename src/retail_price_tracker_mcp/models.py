from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


@dataclass(frozen=True)
class Product:
    id: int | None
    url: str
    adapter: str
    name: str | None = None
    target_price: int | None = None
    notify_on_sale: bool = True
    sizes: list[str] = field(default_factory=list)
    current_price: int | None = None
    currency: str = "TWD"
    active: bool = True
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)


@dataclass(frozen=True)
class CheckResult:
    product_id: int
    name: str | None
    url: str
    adapter: str
    current_price: int | None
    currency: str = "TWD"
    sale_label: str | None = None
    stock_status: str | None = None
    events: list[dict[str, Any]] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)
    checked_at: str = field(default_factory=utc_now_iso)
