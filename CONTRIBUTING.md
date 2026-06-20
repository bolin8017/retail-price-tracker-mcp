# Contributing

Thank you for considering a contribution.

## Development setup

```bash
uv venv
uv pip install -e '.[dev]'
uv run pytest
uv run ruff check .
uv run mypy src
```

## Guidelines

- Add tests for new adapters and service behavior.
- Do not rely on live retailer websites in unit tests.
- Do not fabricate prices, stock status, or sale labels.
- Keep adapters small and documented.
- Use conventional commit-style subjects where practical.
