# Hermes integration

Hermes has a native MCP client. Configure this server in `~/.hermes/config.yaml`:

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

Restart Hermes after changing MCP configuration.

## Cron prompt example

```text
Use the retail price tracker MCP tools to run check_all. If there are price drops, below-target events, sale labels, restocks, or errors needing attention, summarize them for the user in concise Traditional Chinese. If nothing changed, stay silent.
```

## User-facing examples

- “Track this UNIQLO product and notify me below NT$390.”
- “List my tracked retail products.”
- “Show the price history for product 3.”
- “Find candidate UNIQLO products for this OCR text: AIRism 棉質寬版圓領T恤.”
- “Here is a photo of a price tag — find the matching UNIQLO product.”

Use `resolve_product` before `add_product` when the user provides only a product
name, OCR result, or partial product code instead of a canonical URL.

When the user supplies an image of a price label, use `resolve_product_from_image`
with a local image path. OCR runs locally and is an optional extra (PaddleOCR); if
it is not installed the tool returns a clear install error. Always confirm an
ambiguous candidate with the user before calling `add_product`.
