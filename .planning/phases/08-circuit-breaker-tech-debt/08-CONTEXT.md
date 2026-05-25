# Phase 08: Circuit Breaker Tech Debt Cleanup — Context

**Gathered:** 2026-05-26
**Status:** Ready for planning

## Phase Boundary

Fix three remaining Phase 2 circuit breaker gaps: (1) prove `success_threshold` coupling to pybreaker, (2) recreate `_breaker` instances when config changes in `run_job()`, (3) wire retry/breaker into preview curator so preview searches benefit from configured reliability. Also add test coverage for `BreakerConfig`, `_init_breaker()`, `HealthChecker`, and `status_command`.

This is a gap closure phase. All code changes are small (2-5 lines each) and additive — no architectural refactors.

## Implementation Decisions

### Preview Wiring
- **D-01:** Preview command receives retry and breaker config — pass `global_retry=global_config.retry` and `global_breaker=global_config.breaker` to the `Biocurator()` constructor in `preview.py:37`, matching the pattern already used in `status.py:40-44` and `run.py:183-187`.
- **D-02:** Searchers get initialized breakers during construction — call `searcher._breaker = searcher._init_breaker()` in `_init_database_searchers()` after each searcher is created. This gives preview, status, and `run_job()` a working breaker immediately. `run_job()` still overrides with per-db config when needed.
- **Rationale:** Preview calls `searcher.search()` and `searcher.fetch_metadata()` directly without entering `run_job()`. Without `_breaker` initialized, these API calls have no breaker protection — matching the fundamental gap that Phase 7 fixed for `run_job()`.

### Test Coverage
- **D-03:** Unit tests only — all test coverage uses mocks for external APIs (`Bio.Entrez`, `requests`). No integration tests hitting real APIs. Tests are fast, deterministic, and self-contained.
- **D-04:** Test targets:
  - `BreakerConfig.resolve()` — merge priority: per-db > global > pybreaker defaults
  - `BreakerConfig.from_dict()` — YAML parsing path (currently untested)
  - `BreakerConfig.defaults()` — fallback constants (5, 60, 1)
  - `_init_breaker()` — verifies `half_open_max_successes` → `success_threshold` coupling to pybreaker; verifies excluded exception types
  - `HealthChecker.ping_ncbi()` — mocks `Bio.Entrez.esearch`, asserts `HealthStatus` fields
  - `HealthChecker.ping_uniprot()` — mocks `requests.get`, asserts `HealthStatus` fields
  - `status_command` — mocks `ConfigLoader.load()` and `curator.get_health_status()`, asserts Rich table columns, color coding, and edge cases (no providers, single/failing provider)

### success_threshold Verification
- **D-05:** Verify via direct `_init_breaker()` unit test — create a `BreakerConfig(half_open_max_successes=3)`, pass through `resolve()`, inspect the returned `pybreaker.CircuitBreaker` instance's `success_threshold` attribute. One test suffices; the chain is straightforward (config → resolve → CircuitBreaker constructor).
- **Note:** The parameter mapping already exists in code (`base.py:141`: `success_threshold=resolved.half_open_max_successes`). This decision is about how to prove it, not how to implement it.

### Agent's Discretion
- Exact test file placement — new test file (`tests/providers/test_health.py`) or inline in existing files (`tests/providers/test_base.py`, `tests/config/test_schema.py`) based on codebase conventions
- Mock strategy details — `unittest.mock.patch` vs `pytest-mock` fixture vs manual monkeypatch
- Order of test creation — planner determines task sequence based on dependency analysis
- Whether to add `test_status.py` as a new test file or extend `tests/cli/test_run.py`

## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Code to Modify (Phase 8 targets)
- `src/biocurator/cli/commands/preview.py` §L37 — `Biocurator()` constructor call (add `global_retry`/`global_breaker` kwargs)
- `src/biocurator/core/curator.py` §L59-84 — `_init_database_searchers()` (add `_init_breaker()` call per searcher)
- `src/biocurator/providers/base.py` §L134-147 — `_init_breaker()` (target of test coverage for success_threshold)
- `src/biocurator/config/schema.py` §L55-108 — `BreakerConfig` class (target of resolve/from_dict/defaults tests)
- `src/biocurator/providers/health.py` §L16-65 — `HealthChecker` (target of test coverage with mocks)
- `src/biocurator/cli/commands/status.py` §L20-100 — `status_command` (target of test coverage)

### Prior Phase Context (relevant decisions)
- `.planning/phases/02-circuit-breaker-health-status/02-CONTEXT.md` — D-02 (breaker wraps searcher public methods), D-08 (three config knobs), D-10 (merge priority)
- `.planning/phases/07-circuit-breaker-critical-fixes/07-01-SUMMARY.md` — global_breaker wiring fix, deduplicated merge code, breaker_state string fix
- `.planning/phases/07-circuit-breaker-critical-fixes/07-VERIFICATION.md` — confirmed BREAK-01 fix, confirmed breaker_state returns human-readable strings

### Existing Tests (patterns to follow)
- `tests/config/test_schema.py` — RetryConfig test patterns to follow for BreakerConfig tests
- `tests/providers/test_base.py` §L138-150 — Existing `test_breaker_state_returns_state_name_not_object_repr` — creates searcher with BreakerConfig, pattern to extend
- `tests/cli/test_run.py` §L180 — `test_run_main_curator_receives_global_breaker` — mock Biocurator construction, pattern to follow

## Existing Code Insights

### The Key Gap
- `_init_database_searchers()` (curator.py:59-84) creates searchers with `breaker=self.global_breaker` in `DatabaseConfig`, but DOES NOT call `_init_breaker()`. The `_breaker` attribute remains unset until `run_job()` line 198. Preview and status commands call searcher methods directly — without initialized breakers, they lose circuit breaker protection entirely.

### Reusable Assets
- `src/biocurator/providers/base.py:134-147` — `_init_breaker()` already handles `breaker is None` (returns None), excluded exceptions, and all three pybreaker parameters
- `src/biocurator/cli/commands/status.py:40-44` — Already passes `global_retry` and `global_breaker` to Biocurator — pattern to replicate in preview
- `src/biocurator/config/schema.py:56-108` — `BreakerConfig.resolve()` follows same pattern as `RetryConfig.resolve()` — existing test patterns for RetryConfig should be mirrored

### Established Patterns
- **Config dataclass + resolve()**: `RetryConfig.resolve()` tests in `tests/config/test_schema.py` — replicate for `BreakerConfig`
- **CLI → Biocurator constructor**: `status.py:40-44` and `run.py:183-187` both pass all config — add to `preview.py:37`
- **pybreaker constructor call**: `_init_breaker()` creates `CircuitBreaker` with named parameters — test should verify these reach the instance

### Integration Points
- `curator.py:_init_database_searchers()` — add `searcher._breaker = searcher._init_breaker()` after each `ProviderRegistry.get()` call
- `preview.py:37` — add `global_retry=` and `global_breaker=` kwargs
- `tests/config/test_schema.py` — add BreakerConfig tests alongside RetryConfig tests
- `tests/providers/test_base.py` or new `tests/providers/test_health.py` — add `_init_breaker()` and `HealthChecker` tests

## Specific Ideas

- `_init_breaker()` test should verify all three mappings: `fail_max→fail_max`, `recovery_timeout→reset_timeout`, and `half_open_max_successes→success_threshold`
- `_init_breaker()` test should also confirm excluded exceptions list contains `ValueError`, `KeyError`, `TypeError`
- `HealthChecker` tests should verify both reachable (200 response) and unreachable (exception raised) paths for each provider
- `status_command` test should cover: no providers configured, single UP provider, mixed UP/DOWN providers, breaker state display for each state
- The `_init_breaker()` call in `_init_database_searchers()` should handle the `breaker: None` case gracefully — `_init_breaker()` already returns `None` when `self.config.breaker is None`

## Deferred Ideas

None — discussion stayed within phase scope.

---

*Phase: 08-circuit-breaker-tech-debt*
*Context gathered: 2026-05-26*
