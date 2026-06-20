# retail-price-tracker-mcp

[![CI](https://github.com/bolin8017/retail-price-tracker-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/bolin8017/retail-price-tracker-mcp/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

`retail-price-tracker-mcp` is an open-source **Model Context Protocol (MCP) server** for tracking retail product prices. It is designed to work well with [Hermes Agent](https://github.com/NousResearch/hermes-agent), Claude Desktop, Cursor, and any other MCP client.

The first adapter target is **UNIQLO Taiwan**. The project is intentionally adapter-based so future stores such as GU, MUJI, momo, or booksellers can be added without rewriting the tracking core.

> Status: early scaffold / pre-alpha. The current UNIQLO adapter is conservative: it parses supported URLs and records products, but it does not fabricate live prices when a reliable public API is not available.

## Features

- MCP tools for adding, listing, checking, and removing tracked products.
- SQLite persistence for products, price history, and detected events.
- Store adapter architecture.
- UNIQLO Taiwan adapter with search-based current price lookup and safe failure modes.
- Generic static adapter for tests and local demonstrations.
- Optional, local OCR-assisted resolution from a price-label image (PaddleOCR extra).
- Hermes skill package with install/config/cron guidance.
- Standard open-source project files: CI, issue templates, PR template, contributing guide, security policy, code of conduct.

## MCP tools

| Tool | Purpose |
|---|---|
| `add_product` | Add a product URL with optional target price, sale notifications, sizes, and display name. |
| `list_products` | List tracked products. |
| `check_product` | Check one product and record price history/events when possible. |
| `check_all` | Check all active products; useful for cron jobs. |
| `price_history` | Read historical prices for a product. |
| `remove_product` | Deactivate tracking for a product. |
| `resolve_product` | Search adapters for candidate products from a name, OCR text, or product code. |
| `resolve_product_from_image` | Run optional OCR on a local image, then resolve product candidates from the extracted text. |

## Quick start for development

```bash
git clone https://github.com/bolin8017/retail-price-tracker-mcp.git
cd retail-price-tracker-mcp
uv venv
uv pip install -e '.[dev]'
uv run pytest
uv run ruff check .
```

Run the MCP server over stdio:

```bash
PRICE_TRACKER_DB="$PWD/tracker.db" uv run retail-price-tracker-mcp
```

Use the small CLI helper for smoke tests:

```bash
uv run retail-price-tracker add 'https://www.uniqlo.com/tw/zh_TW/products/E123456-000' --name 'Demo shirt' --target-price 390
uv run retail-price-tracker list
uv run retail-price-tracker resolve 'AIRism 棉質寬版圓領T恤' --limit 3
```

### Optional OCR-assisted resolution

OCR is shipped as an optional extra so the core install stays lightweight and
no models are downloaded by default. Install it only when you need to resolve a
product from a photo of a price label:

```bash
uv pip install -e '.[ocr]'   # pulls in PaddleOCR
uv run retail-price-tracker resolve-image /path/to/label.jpg --limit 5
```

The image is run through OCR locally, price/size-only lines are stripped, and the
remaining text becomes a query for `resolve_product`. The project does not build a
custom OCR model; PaddleOCR is the primary engine. Without the extra, the tool
raises a clear error explaining how to install it.

## Hermes configuration

Add this to `~/.hermes/config.yaml`:

```yaml
mcp_servers:
  retail_price_tracker:
    command: "uvx"
    args: ["retail-price-tracker-mcp"]
    env:
      PRICE_TRACKER_DB: "/home/USER/Documents/Hermes/price-tracker/tracker.db"
    timeout: 120
    connect_timeout: 60
```

After restarting Hermes, tools will be available with names like:

```text
mcp_retail_price_tracker_add_product
mcp_retail_price_tracker_check_all
mcp_retail_price_tracker_price_history
mcp_retail_price_tracker_resolve_product
```

See [`docs/hermes.md`](docs/hermes.md) and [`skills/retail-price-tracker/SKILL.md`](skills/retail-price-tracker/SKILL.md) for a full Hermes workflow.

## Example Hermes cron prompt

```text
Use the retail price tracker MCP tools to run check_all. If there are price drops, below-target events, sale labels, restocks, or errors needing attention, summarize them for the user in concise Traditional Chinese. If nothing changed, stay silent.
```

## Design principles

1. **MCP first**: the core should work outside Hermes.
2. **Hermes friendly**: ship a skill and cron templates for a polished Hermes experience.
3. **No fake prices**: adapters must return explicit unsupported/unknown results instead of made-up data.
4. **Local by default**: SQLite on the user's machine; no hosted service required.
5. **Adapter-based**: stores are plugins around a stable tracking core.

## Roadmap

- Harden UNIQLO Taiwan live price fetching with more URL formats and stock detail support.
- Size/color stock tracking.
- Improve OCR resolution accuracy and add an EasyOCR fallback provider.
- changedetection.io backend integration.
- More adapters: GU, MUJI, momo, booksellers.
- HTTP MCP transport and Docker image.

## Security and privacy

Tracked URLs, prices, and shopping preferences are stored locally in SQLite by default. See [`docs/security.md`](docs/security.md).

## Contributing

Please read [`CONTRIBUTING.md`](CONTRIBUTING.md). Bug reports and adapter contributions are welcome.

## License

MIT. See [`LICENSE`](LICENSE).
