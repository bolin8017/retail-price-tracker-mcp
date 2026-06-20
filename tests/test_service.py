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
