# Adapters

Adapters isolate store-specific logic behind a small interface:

- `supports(url) -> bool`
- `check(product) -> CheckResult`
- `resolve(query, limit=5) -> list[dict]`

## Current adapters

| Adapter | Status | Notes |
|---|---|---|
| `generic_static` | Working | Test/demo adapter for `static://` URLs. |
| `uniqlo_tw` | Working search-based fetcher | Parses UNIQLO Taiwan product URLs and uses the public search API to resolve current min price, origin price, sale label, and stock flag. |

## UNIQLO Taiwan notes

The `uniqlo_tw` adapter currently uses:

```text
POST https://d.uniqlo.com/tw/p/search/products/by-description
```

It extracts a query from a UNIQLO URL, such as `E475355-000`, `u0000000053128`,
`productCode=...`, or `pid=...`, then matches the returned `productList`.

The adapter supports both checking known product URLs and resolving candidates
from names/OCR text/product codes. It records:

- `minPrice` as the current tracked price
- `originPrice` in raw metadata
- `priceColor` / product-name hints as sale labels
- `stock` as the stock status flag

If the search API does not return a matching product or the request fails, the
adapter returns an explicit `unsupported_live_fetch` event instead of inventing a
price.

## OCR-assisted resolution

OCR is not an adapter. It is an optional pre-processing layer (`ocr.py`) that turns
an image into text lines, strips price-only and size-only lines, and builds a query
string. That query is then handed to the normal `resolve(query, limit)` path, so OCR
benefits every adapter without store-specific changes. PaddleOCR is the primary
engine and is lazy-imported behind the optional `ocr` extra; tests inject a static
provider so no model is downloaded.

## Adding a store

1. Implement a class in `src/retail_price_tracker_mcp/adapters/`.
2. Add it to `ADAPTERS` in `adapters/__init__.py`.
3. Add tests with mocked/static responses.
4. Document limitations and rate-limiting behavior.
