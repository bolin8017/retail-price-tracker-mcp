# Comprehensive repo review — 2026-07-23

Deep review of all subsystems (service/server/CLI, persistence, adapters, OCR,
tests, CI, docs, packaging). Every finding below was re-verified against the
cited lines; findings marked `[tested]` were reproduced empirically against a
temp database or stubbed responses — never against live user data and with no
live UNIQLO API calls. Verification commands: `uv run pytest`,
`uv run ruff check .`, `uv run mypy src` (all green at HEAD 058c21e).

Severity: **H** user-visible breakage or data loss on realistic input ·
**M** silent misbehavior or broken contract · **L** edge case or hygiene.

## Cross-cutting themes

1. **Failed checks are treated as real observations.** A fetch that learned
   nothing still writes a history row and updates product state. This one
   design gap produces four distinct bugs: stale prices recorded as fresh
   datapoints (adapter-3), the stored price clobbered to NULL (core-2),
   restock detection reset (core-3), and spurious `below_target` events from
   stale data.
2. **Events are level-triggered, but the product contract is edge-triggered.**
   README:116 and docs/hermes.md promise a cron that "stays silent if nothing
   changed", yet `below_target` (core-1) and `stock_status` (adapter-4)
   re-fire on every unchanged check. `price_drop` and `restock` are correctly
   edge-triggered; the others drift from that pattern.
3. **The upsert protects one field out of four.** `add_product` re-add
   preserves `name` via COALESCE but silently wipes `target_price`,
   `notify_on_sale`, and `sizes` (db-1) — the guard exists, just not where the
   user-configured alert settings live.
4. **Tests assert presence, not absence.** Event tests check that events fire
   at boundaries but never that they *don't* fire past them, so several of the
   bugs above are structurally invisible to the current suite (test-2), and
   the generic-adapter double-emit path has no coverage at all (core-5).

## Core (service.py, server.py, cli.py, models.py)

### core-1 · M · `below_target` re-fires on every check `[tested]`
`src/retail_price_tracker_mcp/service.py:60-65`
The event is computed from current state only (`result.current_price <=
target_price`), with no transition check. Scenario: target 390, price stable
at 380 → every `check_all` run emits `below_target`, so the documented
"stay silent if nothing changed" cron (README.md:116, docs/hermes.md) notifies
the user every run, forever. Reproduced: three identical checks → three
`below_target` events.
**Fix**: emit only on the above→at/below transition, mirroring `price_drop`.

### core-2 · M · a no-price check erases the stored price and disables price-drop detection `[tested]`
`src/retail_price_tracker_mcp/db.py:147-150` (via `service.py:54-58`)
`record_check` unconditionally writes `result.current_price` into
`products.current_price`, including `None`. Scenario: price 590 recorded → one
check returns no price (e.g. matched candidate without a parseable `minPrice`)
→ stored price becomes NULL → next check at 390 fires **no** `price_drop`
because there is no baseline. Reproduced end-to-end.
**Fix**: only update `current_price` when the result actually carries a price.

### core-3 · M · restock detection is reset by an intervening failed check `[tested]`
`src/retail_price_tracker_mcp/service.py:50-51, 66-71`
Restock compares only the immediately previous history row. A failed check
writes a row with `stock_status=None`, so the sequence out-of-stock → failed
check → in-stock emits no `restock`. Reproduced: N → None → Y produced no
event. Realistic for any product whose live fetch fails occasionally.
**Fix**: skip no-observation rows when looking up the previous stock state
(fold into the theme-1 batch).

### core-4 · M · `price_history` silently truncates to the 200 most recent rows `[tested]`
`src/retail_price_tracker_mcp/service.py:91-98` + `db.py:168`
The day-window filter runs in Python on `db.history()`'s default
`LIMIT 200`. A product checked hourly exceeds 200 rows in ~8 days, so
`price_history(days=90)` returns ~8 days of data with no truncation signal.
Reproduced: 250 in-window rows recorded, 200 returned.
**Fix**: push the cutoff into SQL (`WHERE checked_at >= ?`) instead of
over-fetching a fixed 200.

### core-5 · L · generic adapter double-emits `below_target` `[tested]`
`src/retail_price_tracker_mcp/adapters/generic.py:16-28` + `service.py:60-65`
Both the adapter and the service append `below_target`, so a `static://`
product at/below target records two identical events per check (cron summary
double-reports). The event-test suite uses a stub adapter that emits nothing,
so it structurally cannot catch this. Reproduced: one check → two events.
**Fix**: the adapter should stop emitting it; event derivation belongs to the
service. Add a real-generic-adapter test asserting exactly one event.

### core-6 · L · importing `server` creates a database as a side effect `[tested]`
`src/retail_price_tracker_mcp/server.py:12`
`TrackerService(TrackerDB(default_db_path()))` runs at module import.
Reproduced: `python -c "import retail_price_tracker_mcp.server"` in an empty
directory creates `tracker.db` there (no `PRICE_TRACKER_DB` set → cwd).
Any tooling that imports the module (inspectors, docs generators) writes a
stray database.
**Fix**: create the service lazily inside `main()` / tool closures.

### core-7 · L · every event row stores prices as old/new values
`src/retail_price_tracker_mcp/db.py:151-166`
`restock`, `stock_status`, and `sale_label` events are written with
`old_value`/`new_value` set to prices, not the actual transition (e.g. N→Y),
making the events table misleading for later analysis.
**Fix**: derive old/new per event type from the event payload.

### core-8 · L · CLI prints raw tracebacks and lacks half the tool surface
`src/retail_price_tracker_mcp/cli.py:31-46`
`check 999` (unknown id) and `resolve-image /missing.jpg` dump stack traces
(ValueError / FileNotFoundError). Exit code is non-zero, so not a false
success — purely UX. `remove`, `check-all`, and `history` have no CLI
equivalent despite being core tools.
**Fix**: wrap dispatch in try/except with concise stderr messages; optionally
add the missing subcommands.

## Persistence (db.py)

### db-1 · H · re-adding a URL silently wipes target price, sale opt-out, and sizes `[tested]`
`src/retail_price_tracker_mcp/db.py:77-84`
`ON CONFLICT(url) DO UPDATE` overwrites `target_price`, `notify_on_sale`, and
`sizes_json` with the new call's values; only `name` is COALESCE-protected.
Scenario: user tracks a product with `target_price=390, notify_on_sale=False,
sizes=["M"]`; any later bare `add_product(url)` (idempotent re-track — the
very case the upsert exists for) resets target to NULL (below-target alerts
never fire again), re-enables sale notifications on a deliberately silenced
product, and clears sizes. Reproduced end-to-end.
**Fix**: preserve existing values when the new call doesn't provide them
(needs a provided-vs-default distinction plumbed from the service), or split
"add" from "update settings".

### db-2 · L · declared foreign keys are never enforced
`src/retail_price_tracker_mcp/db.py:28, 39, 55-62`
No `PRAGMA foreign_keys=ON`, so the `REFERENCES products(id)` clauses are
no-ops; `record_check` against a nonexistent id inserts orphan rows silently.
Low because there is no hard-delete path today.
**Fix**: enable the pragma in `connect()`, or drop the misleading clauses.

### db-3 · L · connections are never explicitly closed
`src/retail_price_tracker_mcp/db.py` (all methods)
`with sqlite3.Connection` commits but does not close; cleanup relies on
CPython refcounting. Harmless today; under PyPy or with an escaping cursor a
lingering read connection blocks WAL checkpointing and grows the `-wal` file.
**Fix**: `contextlib.closing` / try-finally, or a small context-manager helper.

### db-4 · L · no schema-migration mechanism (informational)
`src/retail_price_tracker_mcp/db.py:10-46, 64-66`
Verified: SCHEMA is byte-identical from the initial commit to HEAD, so no
existing database is broken today. But `_init` is `CREATE TABLE IF NOT
EXISTS` only — the first future column addition will silently skip existing
tables and fail at query time.
**Fix**: adopt `PRAGMA user_version` + incremental steps before the first
schema change ships. No code change needed now.

### db-5 · L · `updated_at` is written from adapter-controllable `checked_at`
`src/retail_price_tracker_mcp/db.py:147-150`
A stale or skewed `result.checked_at` moves `products.updated_at` backwards.
Current adapters use the default factory, so latent.
**Fix**: stamp `updated_at` with a fresh `utc_now_iso()`.

## Adapters (uniqlo_tw.py, generic.py)

### adapter-1 · H · no-match search falls back to an arbitrary product's price `[tested]`
`src/retail_price_tracker_mcp/adapters/uniqlo_tw.py:158-174`
When neither the exact `productCode` nor any haystack contains the tracked
code, `_best_match` returns `products[0]` — the first item of a description
search — and `check()` records that product's `minPrice` (and, if the product
has no stored name, its name) as the tracked product's current state,
potentially firing `price_drop`/`below_target` from another product's price.
This directly violates the README "No fake prices" principle. Reproduced at
unit level: code `E471234-000` against an unrelated result list returns the
first unrelated product. The empty-result path is handled and tested
(`test_uniqlo_tw_does_not_fabricate_price_when_no_match`); the
non-empty-no-match path is the untested hole. Triggering requires the search
API to return non-empty fuzzy results for an unmatched code — common search
behavior, though not confirmed against the live API here.
**Fix**: return `None` when there is no confident match so `check()` emits
`unsupported_live_fetch`; keep first-result fallback for `resolve()`
candidates only.

### adapter-2 · M · malformed API responses escape the error handler `[tested]`
`src/retail_price_tracker_mcp/adapters/uniqlo_tw.py:49-52, 103-118, 148-155`
`check()` catches only `httpx.HTTPError`. Reproduced both escapes: an HTTP
200 with a non-JSON body raises `json.JSONDecodeError` (a `ValueError`), and
a JSON array body raises `AttributeError` in `_extract_products` — both
propagate out of `check()`. `check_all` masks this into its `errors` list,
but a single `check_product` MCP call surfaces a raw exception instead of the
documented safe `unsupported_live_fetch` result.
**Fix**: catch `ValueError` too and guard non-dict payloads, funneling both
into `_unsupported()`.

### adapter-3 · M · failed fetches record the stale price as a fresh observation `[tested]`
`src/retail_price_tracker_mcp/adapters/uniqlo_tw.py:120-135` + `service.py:54-65`
`_unsupported()` returns `current_price=product.current_price`, so every
failed check appends a price-history row with a new `checked_at` and the old
price — datapoints that were never fetched — and re-evaluates `below_target`
against stale data (stored 350, target 400, fetch failing → an alert per
run). Reproduced via the event path.
**Fix**: return `current_price=None` from `_unsupported()`; combined with the
core-2 fix the stored price survives and history stays honest.

### adapter-4 · M · stock-flag semantics are guessed, and mismatches spam events
`src/retail_price_tracker_mcp/adapters/uniqlo_tw.py:64, 68-69` + `models.py:12-17`
`is_in_stock` accepts only {Y, YES, IN_STOCK, TRUE, 1}. A missing `stock`
field becomes `"unknown"` (and integer `0` also collapses to `"unknown"` via
`0 or "unknown"`); a numeric quantity like `5` reads as out-of-stock. Any
value outside the set means: a `stock_status` event on **every** check (level-
triggered, theme 2) and `restock` permanently suppressed. Severity kept at M:
the code path is verified, but the live API's actual `stock` values were not
captured in this review — one saved real response would confirm or shrink
this.
**Fix**: capture the real field semantics; treat unknown as indeterminate
(not out-of-stock), map positive numerics to in-stock, and edge-trigger the
`stock_status` event.

### adapter-5 · L · valid UNIQLO URLs rejected on host case or explicit port `[tested]`
`src/retail_price_tracker_mcp/adapters/uniqlo_tw.py:21-23`
`supports()` compares the raw `netloc`. Reproduced:
`https://WWW.UNIQLO.COM/...` and `https://www.uniqlo.com:443/...` both return
False → `choose_adapter` raises "No adapter supports URL" on a valid link.
**Fix**: compare `parsed.hostname.lower()`.

## OCR (ocr.py)

### ocr-1 · M · price hint prefers size numbers over the actual price `[tested]`
`src/retail_price_tracker_mcp/ocr.py:8, 87-94`
`PRICE_RE` matches any 2–7 digit run and `parse_price_hint` returns the
minimum in [10, 100000]. Reproduced: `["W36 L34", "$1,299"]` → hint `34` (a
waist size). Impact bounded — the hint is informational in the resolve
output, never stored as a tracked price.
**Fix**: prefer currency-anchored matches (NT$/TWD/$/元) and fall back to bare
numbers only when none exist.

### ocr-2 · L · product-name lines with any CJK punctuation are discarded `[tested]`
`src/retail_price_tracker_mcp/ocr.py:11, 97-112`
`DESCRIPTION_RE` drops a whole line on a single 、/，/etc. Reproduced:
`"AIRism、涼感T恤"` → hints empty → OCR resolution query loses the product
name entirely.
**Fix**: treat only sentence-like lines (trailing punctuation, long clauses)
as descriptions.

## Tests

### test-1 · M · `price_history` day-window logic is untested
`src/retail_price_tracker_mcp/service.py:91-98` — an exposed MCP tool whose
cutoff parsing/comparison (and the core-4 truncation) has zero coverage; an
aware/naive datetime regression would raise `TypeError` at runtime unseen.
**Fix**: one test inserting rows across the cutoff and asserting the window.

### test-2 · L · event tests assert presence only
`tests/test_check_events.py:69-90` — flipping `price_drop` to `<=` or making
`below_target` unconditional passes the whole suite; there are no
no-event-on-rise / no-event-above-target assertions.
**Fix**: add the negative cases alongside the fixes for core-1/core-5.

### test-3 · L · `is_in_stock` test omits half the accepted values
`tests/test_check_events.py:58-66` — "TRUE" and "1" (in `IN_STOCK_VALUES`)
are unasserted; removing them fails no test.

### test-4 · L · two test files patch two different `ADAPTERS` bindings (informational)
`tests/test_check_events.py:50` patches `adapters_pkg.ADAPTERS` while
`tests/test_service.py:55` patches `service_module.ADAPTERS` — both work only
because `check_product` and `resolve_product` read different bindings
(`service.py:8`). Worth a comment; no code change required.

## CI & tooling

### ci-1 · L · pytest-cov installed on every CI run, never invoked
`pyproject.toml:30` + `.github/workflows/ci.yml:27-28` — no `--cov` anywhere.
**Fix**: wire `--cov=retail_price_tracker_mcp` into CI or drop the dep.

### ci-2 · L · `[tool.mypy] packages` is dead config
`pyproject.toml:63` vs `ci.yml:26` — CI and CONTRIBUTING run `mypy src`,
whose path argument overrides the `packages` setting; bare `uv run mypy` and
CI are different invocations.
**Fix**: standardize on one form (run `uv run mypy` in CI, or delete the
`packages` line).

### ci-3 · L · documented dev install bypasses the lockfile CI uses
`README.md:42` / `CONTRIBUTING.md:9` (`uv pip install -e '.[dev]'`) vs
`ci.yml:22` (`uv sync --extra dev`). Reproduced during review: the pip path
resolved ruff 0.15.22 while the lock pins 0.15.18 — local lint can disagree
with CI.
**Fix**: document `uv sync --extra dev` as the canonical dev setup.

## Docs & packaging

### docs-1 · M · the skill's install-verification command hangs instead of printing help `[tested]`
`skills/retail-price-tracker/SKILL.md:22`
`uvx --from git+… retail-price-tracker-mcp --help` runs `server:main` →
`mcp.run()` (stdio), which never parses argv. Reproduced: the command prints
nothing (blocks on a TTY; exits silently on EOF). A user following the skill
concludes the install is broken. The `retail-price-tracker` CLI entry point
*does* support `--help`.
**Fix**: verify with the CLI entry point instead, or describe the expected
stdio behavior.

### docs-2 · L · CHANGELOG has everything under "Unreleased" at version 0.1.0
`CHANGELOG.md:3` vs `pyproject.toml:7` — a reader checking what shipped in
0.1.0 finds an empty release history.
**Fix**: cut the accumulated entries under a `## 0.1.0` heading.

## Dimensions with no findings

- **SQL injection**: clean — all statements parameterized; the only SQL
  concatenation is a static fragment gated on a bool.
- **SSRF / arbitrary fetch**: clean — user URLs are only parsed, never
  fetched; all network I/O targets the fixed UNIQLO search endpoint.
- **Secrets / committed credentials**: clean — no matches in `git ls-files`;
  `.gitignore` covers `.env` and `*.db*`; SECURITY.md routes through GitHub
  private advisories.
- **Packaging**: clean — entry points resolve, `py.typed` ships in the wheel,
  version and classifiers consistent with `requires-python` and the CI matrix.
- **MCP protocol surface**: clean — tool signatures match service methods;
  `check_all` reports per-product errors instead of masking them.

## Roadmap

Batches in severity order; one batch = one concern = one PR, red test first
(docs/CI batches verified by their artifact's own check instead). Batches are
independent unless noted.

| # | Type | Findings | Concern | Est. size |
|---|------|----------|---------|-----------|
| 1 | fix | adapter-1 | No confident search match → `unsupported_live_fetch`, never `products[0]` | ~60 lines |
| 2 | fix | db-1 | Re-add must not wipe `target_price` / `notify_on_sale` / `sizes` | ~90 lines |
| 3 | fix | adapter-3, core-2, core-3 | Failed checks are no-observations: no stale price rows, no NULL clobber, restock survives gaps | ~130 lines |
| 4 | fix | core-1, core-5, stock-event half of adapter-4 | Edge-trigger `below_target` / `stock_status`; single source of event derivation | ~130 lines |
| 5 | fix | adapter-2 | Malformed API responses funnel into `_unsupported()` | ~40 lines |
| 6 | fix | core-4, test-1 | `price_history`: SQL day cutoff + window tests | ~60 lines |
| 7 | fix | ocr-1, ocr-2 | OCR heuristics: currency-anchored price hint, gentler description filter | ~80 lines |
| 8 | docs | docs-1, docs-2 | SKILL verify command + CHANGELOG 0.1.0 section | ~30 lines |
| 9 | fix | adapter-5 | Hostname normalization in `supports()` | ~20 lines |
| 10 | fix | adapter-4 (semantics half) | Capture real `stock` values; normalize predicate (blocked on one saved live response) | ~50 lines |
| 11 | chore | db-2, db-3, db-5 | SQLite hygiene: FK pragma decision, explicit close, honest `updated_at` | ~60 lines |
| 12 | refactor | core-6 | Lazy service init in `server.py` | ~20 lines |
| 13 | feat | core-8 | CLI error handling + missing subcommands | ~90 lines |
| 14 | test | test-2, test-3 | Negative-path event assertions; complete `is_in_stock` cases | ~60 lines |
| 15 | ci | ci-1, ci-2, ci-3 | Align local/CI toolchain; wire or drop coverage | ~30 lines |
| 16 | chore | core-7 | Event old/new values reflect the actual transition | ~40 lines |

Notes: batch 4 builds on batch 3's "no-observation" concept and lands best
after it; batch 10 needs a captured live API response first. Everything else
is independent. db-4 and test-4 are informational — no batch.
