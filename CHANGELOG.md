# Changelog

## Unreleased

- Initial MCP server scaffold.
- SQLite product and price-history storage.
- Adapter architecture with generic static and UNIQLO Taiwan placeholder adapters.
- Hermes skill and documentation.
- UNIQLO Taiwan search-based price fetcher for current min price, origin price,
  sale hints, and stock flag.
- `resolve_product` MCP tool and CLI command for candidate lookup from names,
  OCR text, or product codes.
- `resolve_product_from_image` MCP tool and `resolve-image` CLI command that run
  optional OCR on a local image, derive a search query from the extracted text,
  and resolve product candidates. OCR is an optional `ocr` extra (PaddleOCR);
  the core install stays lightweight and tests use a static OCR provider.
- `restock` event when a tracked product transitions from out-of-stock to
  in-stock between checks, so cron summaries can report restocks as documented.
- `notify_on_sale` now actually suppresses `sale_label` events when disabled.
- Shared `is_in_stock` stock-flag helper used by the UNIQLO adapter and restock
  detection.
- SQLite connections now use WAL journaling and a busy timeout so the MCP
  server and a cron job can read/write concurrently without lock errors.
- `py.typed` marker so downstream consumers get the package's type hints.
- Install docs now run the server via `uvx --from git+https://...` (or a local
  clone) because the package is not published to PyPI; the previous
  `uvx retail-price-tracker-mcp` examples did not resolve.
