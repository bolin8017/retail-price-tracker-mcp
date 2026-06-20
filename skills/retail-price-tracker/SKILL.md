---
name: retail-price-tracker
description: Track retail product prices via the retail-price-tracker-mcp server; includes Hermes MCP setup and cron workflow.
version: 0.1.0
author: PolinLai
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [mcp, price-tracker, shopping, uniqlo, cron]
---

# Retail Price Tracker

Use this skill when the user wants to track retail product prices, especially UNIQLO Taiwan products, through `retail-price-tracker-mcp`.

## Install

```bash
uvx retail-price-tracker-mcp --help
```

For local development:

```bash
git clone https://github.com/bolin8017/retail-price-tracker-mcp.git
cd retail-price-tracker-mcp
uv venv
uv pip install -e '.[dev]'
```

## Hermes MCP config

Add to `~/.hermes/config.yaml`:

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

Restart Hermes after editing config.

## Common workflow

1. If the user provides a product URL, call `mcp_retail_price_tracker_add_product`.
2. If the user provides only a product name, OCR result, or partial code, call
   `mcp_retail_price_tracker_resolve_product` first and ask them to choose from
   the candidates unless one match is clearly unambiguous.
3. If they specify a target price, pass `target_price` as an integer in local currency.
4. For scheduled checks, create a Hermes cron job that calls `check_all`.
5. Report only meaningful events: price drop, below target, sale, restock, or adapter errors.

## Cron prompt template

```text
Use the retail price tracker MCP tools to run check_all. If there are price drops, below-target events, sale labels, restocks, or errors needing attention, summarize them for the user in concise Traditional Chinese. If nothing changed, stay silent.
```

## Pitfalls

- The `uniqlo_tw` adapter uses UNIQLO Taiwan's search endpoint for current prices.
  If it returns no match or errors, do not invent prices; surface the explicit event.
- If the MCP tools are missing, verify `mcp_servers` config and restart Hermes.
- Use local SQLite paths under `Documents/Hermes/` for user-owned tracker data.
