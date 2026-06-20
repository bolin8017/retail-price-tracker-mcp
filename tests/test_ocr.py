from __future__ import annotations

from typing import Any

import retail_price_tracker_mcp.service as service_module
from retail_price_tracker_mcp.db import TrackerDB
from retail_price_tracker_mcp.ocr import StaticOCRProvider, parse_price_hint, text_hints_from_ocr
from retail_price_tracker_mcp.service import TrackerService


class FakeAdapter:
    name = "fake_store"

    def supports(self, url: str) -> bool:
        return False

    def check(self, product: Any) -> Any:
        raise AssertionError("not used")

    def resolve(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        assert query == "AIRism Cotton Oversized Crew Neck T-Shirt AIRism 棉質寬版圓領T恤"
        return [
            {
                "adapter": self.name,
                "product_code": "demo-1",
                "name": "AIRism 棉質寬版圓領T恤",
                "url": "static://demo-1",
                "current_price": 590,
                "origin_price": 790,
                "currency": "TWD",
                "sale_label": None,
                "stock_status": "Y",
                "raw": {},
            }
        ]


def test_parse_price_hint_from_ocr_lines():
    assert parse_price_hint(["AIRism Cotton", "NT$590", "S M L XL XXL"]) == 590


def test_text_hints_from_ocr_lines_discards_price_and_sizes():
    lines = ["AIRism Cotton Oversized Crew Neck T-Shirt", "NT$590", "S M L XL XXL"]
    assert text_hints_from_ocr(lines) == ["AIRism Cotton Oversized Crew Neck T-Shirt"]


def test_resolve_product_from_image_uses_injected_ocr_provider(monkeypatch, tmp_path):
    image = tmp_path / "label.jpg"
    image.write_bytes(b"fake image bytes")
    provider = StaticOCRProvider(
        lines=[
            "AIRism Cotton Oversized Crew Neck T-Shirt",
            "AIRism 棉質寬版圓領T恤",
            "NT$590",
            "S M L XL XXL",
        ]
    )
    monkeypatch.setattr(service_module, "ADAPTERS", [FakeAdapter()])

    service = TrackerService(TrackerDB(tmp_path / "tracker.db"), ocr_provider=provider)
    result = service.resolve_product_from_image(str(image), limit=3)

    assert result["ocr"] == {
        "provider": "static",
        "text_lines": [
            "AIRism Cotton Oversized Crew Neck T-Shirt",
            "AIRism 棉質寬版圓領T恤",
            "NT$590",
            "S M L XL XXL",
        ],
        "price_hint": 590,
        "query": "AIRism Cotton Oversized Crew Neck T-Shirt AIRism 棉質寬版圓領T恤",
    }
    assert result["candidates"][0]["name"] == "AIRism 棉質寬版圓領T恤"


def test_resolve_product_from_image_rejects_missing_file(tmp_path):
    service = TrackerService(TrackerDB(tmp_path / "tracker.db"), ocr_provider=StaticOCRProvider([]))
    missing = tmp_path / "missing.jpg"
    try:
        service.resolve_product_from_image(str(missing))
    except FileNotFoundError as exc:
        assert str(missing) in str(exc)
    else:
        raise AssertionError("expected FileNotFoundError")


def test_lines_from_paddle_result_parses_v3_rec_texts():
    # PaddleOCR 3.x predict() returns dict-like OCRResult objects whose
    # recognized strings live under "rec_texts".
    from retail_price_tracker_mcp.ocr import _lines_from_paddle_result

    raw = [{"rec_texts": ["AIRism Cotton", "NT$590", "  "], "rec_scores": [0.99, 0.98, 0.1]}]
    assert _lines_from_paddle_result(raw) == ["AIRism Cotton", "NT$590"]
