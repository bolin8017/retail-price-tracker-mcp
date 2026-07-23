# Contributing

Thank you for considering a contribution.

## Development setup

Use `uv sync` so your tool versions match the lockfile CI uses (a plain
`uv pip install` resolves fresh and can drift from CI):

```bash
uv sync --extra dev
uv run pytest --cov=retail_price_tracker_mcp
uv run ruff check .
uv run mypy
```

## Guidelines

- Add tests for new adapters and service behavior.
- Do not rely on live retailer websites in unit tests.
- Do not fabricate prices, stock status, or sale labels.
- Keep adapters small and documented.
- Use conventional commit-style subjects where practical.
