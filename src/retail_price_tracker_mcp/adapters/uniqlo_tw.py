from __future__ import annotations

import re
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx

from retail_price_tracker_mcp.models import CheckResult, Product, is_in_stock

UNIQLO_TW_HOSTS = {"www.uniqlo.com", "uniqlo.com"}
UNIQLO_TW_SEARCH_URL = "https://d.uniqlo.com/tw/p/search/products/by-description"
PRODUCT_RE = re.compile(r"/(?:tw/)?(?:zh_TW/)?products/(?P<code>[A-Za-z0-9_-]+)")
UNIQLO_NUMERIC_CODE_RE = re.compile(r"(?<!\d)(\d{6})(?!\d)")
UNIQLO_INTERNAL_CODE_RE = re.compile(r"u\d{13}", re.IGNORECASE)


class UniqloTwAdapter:
    name = "uniqlo_tw"

    def supports(self, url: str) -> bool:
        parsed = urlparse(url)
        if parsed.netloc not in UNIQLO_TW_HOSTS or "/tw/" not in parsed.path:
            return False
        if "/products/" in parsed.path:
            return True
        query = parse_qs(parsed.query)
        return "productCode" in query or "pid" in query

    def parse_product_code(self, url: str) -> str | None:
        parsed = urlparse(url)
        for key in ("productCode", "pid"):
            value = parse_qs(parsed.query).get(key, [None])[0]
            if value:
                return value
        match = PRODUCT_RE.search(parsed.path)
        if match:
            return match.group("code")
        internal_match = UNIQLO_INTERNAL_CODE_RE.search(url)
        if internal_match:
            return internal_match.group(0)
        return None

    def check(self, product: Product) -> CheckResult:
        code = self.parse_product_code(product.url)
        if not code:
            return self._unsupported(product, "Could not parse a product code from the URL.")

        try:
            candidate = self._fetch_product_by_code(code)
        except httpx.HTTPError as exc:
            return self._unsupported(product, f"UNIQLO Taiwan search request failed: {exc}")

        if candidate is None:
            return self._unsupported(
                product,
                "UNIQLO Taiwan search API returned no matching product for this code.",
                raw={"product_code": code},
            )

        current_price = _coerce_int(candidate.get("minPrice"))
        origin_price = _coerce_int(candidate.get("originPrice"))
        sale_label = _sale_label(candidate)
        stock_status = str(candidate.get("stock") or "unknown")
        events: list[dict[str, Any]] = []
        if sale_label:
            events.append({"event_type": "sale_label", "label": sale_label})
        if not is_in_stock(stock_status):
            events.append({"event_type": "stock_status", "stock_status": stock_status})

        return CheckResult(
            product_id=product.id or 0,
            name=product.name or _clean_product_name(candidate),
            url=product.url,
            adapter=self.name,
            current_price=current_price,
            currency=product.currency,
            sale_label=sale_label,
            stock_status=stock_status,
            events=events,
            raw={
                "source": "uniqlo_tw_search_api",
                "product_code": code,
                "matched_product_code": candidate.get("productCode"),
                "origin_price": origin_price,
                "price_color": candidate.get("priceColor"),
                "product_name": candidate.get("productName") or candidate.get("name"),
                "pub_suffix": candidate.get("pubSuffix"),
                "default_color": candidate.get("defaultColor"),
                "main_pic": candidate.get("mainPic"),
            },
        )

    def _fetch_product_by_code(self, code: str) -> dict[str, Any] | None:
        query = _search_query_for_code(code)
        products = self._search_products(query, limit=20)
        return _best_match(products, code)

    def resolve(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        products = self._search_products(query, limit=limit)
        return [_candidate_from_product(product) for product in products[:limit]]

    def _search_products(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        response = httpx.post(
            UNIQLO_TW_SEARCH_URL,
            json={"description": query, "page": 1, "pageSize": limit},
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "retail-price-tracker-mcp/0.1",
                "Referer": "https://www.uniqlo.com/tw/zh_TW/",
                "langCode": "zh_TW",
            },
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        return _extract_products(payload)

    def _unsupported(
        self,
        product: Product,
        message: str,
        raw: dict[str, Any] | None = None,
    ) -> CheckResult:
        return CheckResult(
            product_id=product.id or 0,
            name=product.name,
            url=product.url,
            adapter=self.name,
            current_price=product.current_price,
            currency=product.currency,
            events=[{"event_type": "unsupported_live_fetch", "message": message}],
            raw=raw or {"live_fetch": "unsupported", "message": message},
        )


def _search_query_for_code(code: str) -> str:
    internal = UNIQLO_INTERNAL_CODE_RE.search(code)
    if internal:
        return internal.group(0)
    numeric = UNIQLO_NUMERIC_CODE_RE.search(code)
    if numeric:
        return numeric.group(1)
    return code


def _extract_products(payload: dict[str, Any]) -> list[dict[str, Any]]:
    products: list[dict[str, Any]] = []
    for block in payload.get("resp") or []:
        if isinstance(block, dict):
            for item in block.get("productList") or []:
                if isinstance(item, dict):
                    products.append(item)
    return products


def _best_match(products: list[dict[str, Any]], code: str) -> dict[str, Any] | None:
    if not products:
        return None
    normalized = code.lower()
    search_code = _search_query_for_code(code).lower()
    for product in products:
        product_code = str(product.get("productCode") or "").lower()
        if product_code and product_code in {normalized, search_code}:
            return product
    for product in products:
        haystack = " ".join(
            str(product.get(key) or "")
            for key in ("productName", "name", "shortName", "productCode", "omsProductCode")
        ).lower()
        if normalized in haystack or search_code in haystack:
            return product
    return products[0]


def _coerce_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(str(value).replace(",", "")))
    except ValueError:
        return None


def _sale_label(product: dict[str, Any]) -> str | None:
    product_name = str(product.get("productName") or product.get("name") or "")
    price_color = str(product.get("priceColor") or "").lower()
    origin_price = _coerce_int(product.get("originPrice"))
    min_price = _coerce_int(product.get("minPrice"))
    if "特價" in product_name:
        return "特價商品"
    if price_color == "red":
        return "sale"
    if origin_price is not None and min_price is not None and min_price < origin_price:
        return "price_below_origin"
    return None


def _clean_product_name(product: dict[str, Any]) -> str | None:
    name = product.get("shortName") or product.get("name") or product.get("productName")
    return str(name) if name else None


def _style_code(product: dict[str, Any]) -> str | None:
    # The 6-digit style code is what the description-search API can actually find;
    # the internal `productCode` (u + 13 digits) cannot be looked up by search.
    for key in ("code", "masterSpuCode"):
        match = UNIQLO_NUMERIC_CODE_RE.search(str(product.get(key) or ""))
        if match:
            return match.group(1)
    name = str(product.get("productName") or product.get("name") or "")
    match = UNIQLO_NUMERIC_CODE_RE.search(name)
    return match.group(1) if match else None


def _candidate_url(product: dict[str, Any], product_code: str) -> str:
    # Prefer a URL whose code is searchable, so check_product can re-fetch it.
    style_code = _style_code(product)
    if style_code:
        pub_suffix = str(product.get("pubSuffix") or "000")
        return f"https://www.uniqlo.com/tw/zh_TW/products/E{style_code}-{pub_suffix}"
    return f"https://www.uniqlo.com/tw/zh_TW/product-detail.html?productCode={product_code}"


def _candidate_from_product(product: dict[str, Any]) -> dict[str, Any]:
    product_code = str(product.get("productCode") or "")
    return {
        "adapter": "uniqlo_tw",
        "product_code": product_code,
        "name": _clean_product_name(product),
        "url": _candidate_url(product, product_code),
        "current_price": _coerce_int(product.get("minPrice")),
        "origin_price": _coerce_int(product.get("originPrice")),
        "currency": "TWD",
        "sale_label": _sale_label(product),
        "stock_status": str(product.get("stock") or "unknown"),
        "raw": {
            "price_color": product.get("priceColor"),
            "pub_suffix": product.get("pubSuffix"),
            "default_color": product.get("defaultColor"),
        },
    }
