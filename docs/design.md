# Design

`retail-price-tracker-mcp` separates tracking into four layers:

1. **MCP interface**: stable tools exposed to agents.
2. **Service layer**: product lifecycle, event generation, history writes.
3. **Persistence**: local SQLite by default.
4. **Store adapters**: store-specific URL parsing and price/stock fetching.

The server is intentionally local-first. It returns structured events and leaves notification delivery to the MCP client, such as Hermes Cron delivering to Telegram or Discord.

## Event model

Adapters return observations. The service compares observations against stored state and target prices to create events such as `price_drop`, `below_target`, `sale_label`, or `unsupported_live_fetch`.

## Safety

Adapters must never invent prices. If a live price cannot be verified, return `current_price: null` with an explicit event/error.
