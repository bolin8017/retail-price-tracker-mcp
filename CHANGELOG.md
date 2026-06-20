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
- SQLite connections now use WAL journaling and a busy timeout so the MCP
  server and a cron job can read/write concurrently without lock errors.
- `py.typed` marker so downstream consumers get the package's type hints.
