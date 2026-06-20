# Security and privacy

- Product URLs, target prices, and history are stored in local SQLite by default.
- The server does not require API keys for the current adapters.
- Do not commit real tracker databases; `*.db` is ignored.
- Store adapters should use conservative request rates and respect robots/terms.
- Never fabricate prices or stock status. Unknown data must be represented as `null` plus an explicit event/error.

To report vulnerabilities, see `SECURITY.md`.
