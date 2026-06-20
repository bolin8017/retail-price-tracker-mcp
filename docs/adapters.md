# Adapters

Adapters isolate store-specific logic behind a small interface:

- `supports(url) -> bool`
- `check(product) -> CheckResult`

## Current adapters

| Adapter | Status | Notes |
|---|---|---|
| `generic_static` | Working | Test/demo adapter for `static://` URLs. |
| `uniqlo_tw` | Placeholder | Parses UNIQLO Taiwan product URLs but does not yet perform reliable live price fetching. |

## Adding a store

1. Implement a class in `src/retail_price_tracker_mcp/adapters/`.
2. Add it to `ADAPTERS` in `adapters/__init__.py`.
3. Add tests with mocked/static responses.
4. Document limitations and rate-limiting behavior.
