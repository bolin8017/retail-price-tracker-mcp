# Changelog

## Unreleased

- UNIQLO checks never guess anymore: a search with no confident match returns
  `unsupported_live_fetch` instead of recording another product's price, and
  malformed API responses (non-JSON, unexpected shape) take the same safe path.
- Re-adding a tracked URL preserves the stored target price, sale opt-out, and
  sizes; omitted fields keep their values instead of resetting to defaults.
- Failed checks are recorded as "no observation": they no longer erase the
  stored price baseline, fabricate fresh-looking history datapoints from stale
  prices, or mask restock detection. A missing UNIQLO `stock` field counts as
  no observation too (confirmed against a live API capture).
- `below_target` and out-of-stock events are edge-triggered — they fire when
  the state is entered, not on every check while it persists, so cron
  summaries stay silent when nothing changed.
- `price_history` honors the full `days` window instead of silently capping at
  the 200 most recent rows.
- OCR resolution: price hints prefer currency-anchored numbers over sizes and
  measurements, and short product-name lines with CJK punctuation are kept.
- CLI: new `check-all`, `history`, and `remove` subcommands; expected errors
  print concise messages instead of tracebacks.
- SQLite hygiene: foreign keys enforced, connections closed deterministically,
  `updated_at` uses the wall clock, and event rows describe their own
  transition instead of always storing prices.
- Docs/CI: the skill's install-verification command now actually prints help,
  `uv sync --extra dev` is the canonical dev setup matching CI's lockfile, and
  CI measures coverage.

## 0.1.0 - 2026-07-23

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
- OCR now actually runs: the `ocr` extra also installs the `paddlepaddle`
  runtime, and the PaddleOCR provider was updated to the 3.x API (`predict()` +
  `rec_texts`) with oneDNN disabled to avoid a PP-OCRv6 inference crash on some
  CPUs.
- Fix the resolve → track → check chain. `resolve_product` now builds UNIQLO
  URLs from the searchable style code (`products/E<code>-000`) instead of the
  internal `productCode`, so a product found by name/photo can actually be
  price-checked. OCR query building also drops marketing/disclaimer sentences,
  so a real in-store product-sign photo resolves to candidates instead of none.
