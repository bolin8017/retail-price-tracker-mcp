# Security and privacy

- Product URLs, target prices, and history are stored in local SQLite by default.
- The server does not require API keys for the current adapters.
- Do not commit real tracker databases; `*.db` is ignored.
- Store adapters should use conservative request rates and respect robots/terms.
- Never fabricate prices or stock status. Unknown data must be represented as `null` plus an explicit event/error.
- OCR is optional and processes images locally. Images of price labels may contain
  private shopping or location information, so the `resolve_product_from_image` flow
  reads files from a local path and sends them only to the locally-run OCR engine.
- OCR models are never downloaded in CI; tests use a static OCR provider, and OCR
  text must not be fabricated.

To report vulnerabilities, see `SECURITY.md`.
