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
- `restock` event when a tracked product transitions from out-of-stock to
  in-stock between checks, so cron summaries can report restocks as documented.
- `notify_on_sale` now actually suppresses `sale_label` events when disabled.
- Shared `is_in_stock` stock-flag helper used by the UNIQLO adapter and restock
  detection.
