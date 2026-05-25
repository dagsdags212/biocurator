---
phase: 02
plan: 02-02
subsystem: "Circuit Breaker & Health Status"
tags:
  - circuit-breaker
  - health-check
  - pybreaker
  - searcher-integration
dependency_graph:
  requires:
    - "02-01 (BreakerConfig foundation / pybreaker dep / schema fields)"
  provides:
    - "02-03 (CLI status command — needs HealthChecker merge)"
  affects:
    - src/biocurator/providers/health.py (NEW)
    - src/biocurator/providers/base.py
    - src/biocurator/providers/ncbi/searcher.py
    - src/biocurator/providers/uniprot/searcher.py
    - src/biocurator/core/curator.py
tech-stack:
  added:
    - pybreaker.CircuitBreaker for provider searchers
  patterns:
    - "_do_* helper extraction for breaker wrapping"
    - "generator function wrapping with CircuitBreaker.call()"
    - "merge priority: per-database > global > pybreaker defaults"
key-files:
  created:
    - src/biocurator/providers/health.py
  modified:
    - src/biocurator/providers/base.py
    - src/biocurator/providers/ncbi/searcher.py
    - src/biocurator/providers/uniprot/searcher.py
    - src/biocurator/core/curator.py
decisions:
  - "Breaker wraps generator function call (not iteration) per pybreaker contract"
  - "Failure classification excludes ValueError, KeyError, TypeError as non-network"
  - "Merge priority: per-database breaker override > global breaker > BreakerConfig.defaults()"
metrics:
  duration: "3 min"
  completed_date: "2026-05-25"
---

# Phase 2 Plan 2: Circuit Breaker + HealthChecker Integration Summary

Created HealthChecker for lightweight provider health probes and integrated pybreaker circuit breakers into all provider searchers. Circuit breaker wraps searcher public methods (search, fetch_metadata, download) so that when a provider server is unreachable, the breaker opens after fail_max failures and subsequent calls fail fast.

## Tasks Executed

### Task 1a — Create HealthChecker (NEW)
- Created `src/biocurator/providers/health.py` with `HealthStatus` dataclass and `HealthChecker` with `ping_ncbi()` and `ping_uniprot()` static methods
- Each ping returns reachable bool, response time in ms, and optional error
- **Commit:** `97929b4`

### Task 1b — Breaker support in DatabaseSearcher base
- Added `import pybreaker` to `base.py`
- Added `_init_breaker()` to `DatabaseSearcher` — creates `pybreaker.CircuitBreaker` from `self.config.breaker`
- Added `breaker_state` property returning the breaker's current state
- **Commit:** `97929b4`

### Task 2a — Breaker integration into NCBISearcher
- Added `import pybreaker`, `self._breaker` init in `__init__` with logging
- Extracted `_do_search()` — search logic only (returns list[str])
- Extracted `_do_fetch_metadata()` — generator body (returns Iterator)
- Extracted `_do_download()` — generator body (returns Iterator)
- Public methods now wrap with `self._breaker.call()` when breaker exists
- **Commit:** `310964e`

### Task 2b — Breaker integration into UniProtSearcher
- Same pattern as NCBI: added pybreaker import, `_do_*` extraction, breaker wrapping
- **Commit:** `310964e`

### Task 3 — Wire breaker config through Biocurator init
- Added `global_breaker: BreakerConfig | None = None` parameter to `Biocurator.__init__()`
- Passed `breaker=self.global_breaker` to both `DatabaseConfig` constructor calls in `_init_database_searchers()`
- Added breaker merge logic in `run_job()`: per-database > global > pybreaker defaults
- **Commit:** `3cdeac6`

## Verification

| Check | Result |
|-------|--------|
| `HealthChecker` imports | ✅ |
| `Biocurator('t@t.com')` — no breaker | ✅ All searchers have `_breaker is None` |
| `Biocurator('t@t.com', global_breaker=BreakerConfig(fail_max=5))` — with breaker | ✅ Both searchers have closed-circuit breaker |
| `breaker_state` property | ✅ Returns `CircuitClosedState` for active breakers |
| Full test suite (154 tests) | ✅ PASSED (0.42s) |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None detected.

## Threat Flags

None — HealthChecker makes outbound HTTP calls only; no new endpoints exposed.

## Self-Check: PASSED

All verification commands executed successfully, all 154 tests pass.
