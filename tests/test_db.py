from retail_price_tracker_mcp.db import TrackerDB
from retail_price_tracker_mcp.models import CheckResult, Product


def test_add_list_and_remove_product(tmp_path):
    db = TrackerDB(tmp_path / "tracker.db")
    product = db.add_product(
        Product(
            id=None,
            url="static://shirt",
            adapter="generic_static",
            name="Demo",
            target_price=390,
        )
    )
    assert product.id is not None
    assert db.list_products()[0].name == "Demo"
    assert db.deactivate_product(product.id)
    assert db.list_products(active_only=True) == []
    assert len(db.list_products(active_only=False)) == 1


def test_connection_uses_wal_and_busy_timeout(tmp_path):
    db = TrackerDB(tmp_path / "tracker.db")
    with db.connect() as conn:
        journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        busy_timeout = conn.execute("PRAGMA busy_timeout").fetchone()[0]
    assert journal_mode.lower() == "wal"
    assert busy_timeout >= 1000


def test_event_values_reflect_the_event_type(tmp_path):
    # A restock row must not be described by price numbers, and a sale row
    # should carry its label; otherwise the events table misleads later
    # analysis ("restock: 590 -> 590").
    db = TrackerDB(tmp_path / "tracker.db")
    product = db.add_product(Product(id=None, url="static://shirt", adapter="generic_static"))
    db.record_check(
        CheckResult(
            product_id=product.id or 0,
            name="Demo",
            url="static://shirt",
            adapter="generic_static",
            current_price=590,
            stock_status="Y",
            events=[
                {"event_type": "restock"},
                {"event_type": "sale_label", "label": "sale"},
                {"event_type": "price_drop"},
            ],
        )
    )
    with db.connect() as conn:
        rows = {
            row["event_type"]: row
            for row in conn.execute("SELECT event_type, old_value, new_value FROM events")
        }
    assert rows["restock"]["new_value"] == "Y"
    assert rows["sale_label"]["new_value"] == "sale"
    assert rows["price_drop"]["new_value"] == "590"


def test_record_history(tmp_path):
    db = TrackerDB(tmp_path / "tracker.db")
    product = db.add_product(Product(id=None, url="static://shirt", adapter="generic_static"))
    db.record_check(
        CheckResult(
            product_id=product.id or 0,
            name="Demo",
            url="static://shirt",
            adapter="generic_static",
            current_price=590,
        )
    )
    history = db.history(product.id or 0)
    assert history[0]["price"] == 590
