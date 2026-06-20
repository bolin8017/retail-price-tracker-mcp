from retail_price_tracker_mcp.adapters.uniqlo_tw import UniqloTwAdapter
from retail_price_tracker_mcp.models import Product


def test_uniqlo_tw_supports_product_url():
    adapter = UniqloTwAdapter()
    url = "https://www.uniqlo.com/tw/zh_TW/products/E471234-000"
    assert adapter.supports(url)
    assert adapter.parse_product_code(url) == "E471234-000"


def test_uniqlo_tw_does_not_fabricate_price():
    adapter = UniqloTwAdapter()
    product = Product(
        id=1,
        url="https://www.uniqlo.com/tw/zh_TW/products/E471234-000",
        adapter=adapter.name,
    )
    result = adapter.check(product)
    assert result.current_price is None
    assert result.events[0]["event_type"] == "unsupported_live_fetch"
