from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .config import default_db_path
from .db import TrackerDB
from .service import TrackerService

mcp = FastMCP("retail-price-tracker")
_service = TrackerService(TrackerDB(default_db_path()))


@mcp.tool()
def add_product(
    url: str,
    target_price: int | None = None,
    notify_on_sale: bool = True,
    sizes: list[str] | None = None,
    name: str | None = None,
) -> dict[str, Any]:
    """Add a retail product URL to the tracker."""
    return _service.add_product(url, target_price, notify_on_sale, sizes, name)


@mcp.tool()
def list_products(active_only: bool = True) -> dict[str, Any]:
    """List tracked products."""
    return _service.list_products(active_only)


@mcp.tool()
def check_product(product_id: int) -> dict[str, Any]:
    """Check one product and record history/events."""
    return _service.check_product(product_id)


@mcp.tool()
def check_all() -> dict[str, Any]:
    """Check all active products; useful for scheduled jobs."""
    return _service.check_all()


@mcp.tool()
def price_history(product_id: int, days: int = 90) -> dict[str, Any]:
    """Return price history for a product."""
    return _service.price_history(product_id, days)


@mcp.tool()
def remove_product(product_id: int) -> dict[str, Any]:
    """Deactivate tracking for a product."""
    return _service.remove_product(product_id)


@mcp.tool()
def resolve_product(query: str, limit: int = 5) -> dict[str, Any]:
    """Search store adapters for product candidates matching a query."""
    return _service.resolve_product(query, limit)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
