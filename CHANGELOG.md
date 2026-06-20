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
