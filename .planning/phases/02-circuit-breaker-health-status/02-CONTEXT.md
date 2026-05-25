# Phase 2: Circuit Breaker & Health Status — Context

**Gathered:** 2026-05-25
**Status:** Ready for planning

## Phase Boundary

Per-provider circuit breakers that prevent cascading failures when a server is down, plus `biocurator status` CLI command for health probing and breaker state observability. This phase covers the breaker integration into the provider layer and the status command — NOT pre-flight check integration (that's Phase 5).

## Implementation Decisions

### Circuit Breaker Library
- **D-01:** Use **pybreaker** — mature single-dependency library with open/closed/half-open states, exception exclusion by type/predicate, listener callbacks for state changes, and named instances for logging.
- **Rationale:** Handles all 3 states out of the box, supports event callbacks (state change logging), and `exclude=[...]` lets us filter non-retryable exceptions from tripping the breaker.

### Breaker Placement
- **D-02:** Breaker wraps **searcher public methods** (`search()`, `fetch_metadata()`, `download()`) at the `DatabaseSearcher` level — not individual HTTP calls or `_safe_*` helpers.
- **D-03:** Only `DatabaseSearchError` (from `search()`) and unhandled exceptions from generators count as breaker failures. Non-retryable exceptions (ValueError, KeyError, 4xx) are excluded from breaker counting via pybreaker's `exclude=`.
- **Rationale:** Retry handles transient blips at the HTTP level; breaker catches sustained failures after retry exhausts. Wrapping public methods means the breaker sits outside the retry loop — clean separation of concerns.

### Health Check Approach
- **D-04:** Lightweight ping — minimal API call (not a full search) to measure reachability and response time.
- **For NCBI:** `Entrez.esearch(db="nuccore", term="a[organism]", retmax=1)` — minimal query guaranteed to return results.
- **For UniProt:** `GET /uniprotkb/search?query=a&size=1` — minimal query.
- **D-05:** Response time is measured and reported in milliseconds. Timeout uses the provider-configured `timeout` value.
- **Rationale:** Fast, low-overhead, respects rate limits. A single successful ping confirms the server is accepting requests, which is sufficient for a status check.

### status CLI Output
- **D-06:** `biocurator status` displays a **Rich table** with columns: Provider, Status (color-coded UP/DOWN/UNKNOWN), Response Time, Breaker State (open/closed/half-open).
- **D-07:** Format: one row per configured provider (ncbi, uniprot). Color coding: green for UP/closed, yellow for half-open, red for DOWN/open.
- **Rationale:** Scannable at a glance, consistent with existing CLI output patterns (Rich tables in `preview` and `run` commands).

### Circuit Breaker Config
- **D-08:** Expose three knobs in `DatabaseConfig` with `None` defaults (backward compatible):
  - `fail_max`: int (default 5) — consecutive failures before breaker opens
  - `recovery_timeout`: int (default 60) — seconds before half-open trial
  - `half_open_max_successes`: int (default 1) — successes needed in half-open to close
- **D-09:** Config naming follows Phase 1 pattern: `DatabaseConfig.breaker: BreakerConfig | None` where `BreakerConfig` is a new dataclass in `config/schema.py`.
- **D-10:** Merge priority (same pattern as retry): per-database override > global defaults > pybreaker defaults.

### Agent's Discretion
- Breaker instance creation pattern — whether to create a shared breaker per searcher or per call (recommended: one breaker instance per searcher, stored as `self._breaker`)
- Listener implementation details — logging state changes is expected; whether to also expose metrics is discretionary
- `HealthChecker` class location — could be `providers/health.py` or `utils/health.py`; architecturally it fits best in `providers/` since it's provider-specific logic
- Whether `biocurator status` also accepts a `--provider` flag to check a single provider

## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing Code Patterns
- `src/biocurator/providers/base.py` — `DatabaseSearcher` ABC and `DatabaseConfig` dataclass (add `BreakerConfig` and breaker instances here)
- `src/biocurator/config/schema.py` — `RetryConfig` pattern to follow for `BreakerConfig`
- `src/biocurator/config/loader.py` — YAML parsing pattern for optional config blocks
- `src/biocurator/cli/commands/preview.py` — Rich table pattern to follow for `status` command output
- `src/biocurator/cli/main.py` — Typer app definition; add `status` command
- `src/biocurator/exceptions.py` — Add `CircuitBreakerError` if needed for typed handling

### Dependencies
- pybreaker — added to `pyproject.toml` dependencies

## Existing Code Insights

### Reusable Assets
- `src/biocurator/utils/retryable_exceptions.py` — `_is_retryable()` predicate can be reused to exclude non-retryable exceptions from breaker counting
- `src/biocurator/providers/registry.py` — `ProviderRegistry` provides `available()` method for enumerating providers in status command
- `src/biocurator/cli/commands/run.py` — Typer `@app.command()` pattern and Rich `Progress` table setup

### Established Patterns
- **Config dataclass + YAML parsing**: `RetryConfig` in `schema.py` + loader parsing → replicate for `BreakerConfig`
- **Searcher initialization**: `_init_database_searchers()` creates configs with retry → add breaker to the same flow
- **CLI command**: `@app.command()` with `Annotated` options in `commands/` → `status_command` follows same pattern
- **Rich output**: Tables in `preview.py`, progress bars in `run.py` → same library for status

### Integration Points
- `Biocurator.__init__()` — pass breaker config, create breaker instances
- `Biocurator._init_database_searchers()` — attach breaker to each searcher
- `Biocurator.run_job()` — breaker wraps `searcher.search()` call
- `cli/main.py` — register `status` Typer command
- `Biocurator` class — add `get_health_status()` method or similar

## Specific Ideas

- pybreaker `name=` parameter should include provider name (e.g., "ncbi-breaker") for log identification
- State change listeners should log state transitions at `WARNING` level (important operational signal)
- Status command should handle `DatabaseSearchError` gracefully (catch and report as DOWN, don't crash)
- Breaker state should be exposed via a property on the searcher (e.g., `searcher.breaker_state`) for status command to read

## Deferred Ideas

- **Checkpoint persistence** (V2-01): Persistent breaker state across process restarts — deferred to v2
- **`--watch` mode** (V2-02): Continuous monitoring with configurable interval — deferred to v2
- **Pre-flight check integration** (STATUS-04, CFG-03): `biocurator run --check` — part of Phase 5

---
*Phase: 02-circuit-breaker-health-status*
*Context gathered: 2026-05-25*
