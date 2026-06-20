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
