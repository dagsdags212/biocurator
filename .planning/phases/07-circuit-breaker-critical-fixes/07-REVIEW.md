---
phase: 07-circuit-breaker-critical-fixes
reviewed: 2026-05-26T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - src/biocurator/cli/commands/run.py
  - src/biocurator/core/curator.py
  - tests/cli/test_run.py
  - tests/providers/test_base.py
findings:
  critical: 0
  warning: 2
  info: 4
  total: 6
status: issues_found
---

# Phase 07: Code Review Report

**Reviewed:** 2026-05-26
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Reviewed the circuit breaker critical fixes phase with focus on:
1. **BREAK-01 fix** — global_breaker wiring in run.py main curator constructor
2. **Deduplication** — removed duplicate breaker merge code in curator.py
3. **Regression test** — test_run_main_curator_receives_global_breaker
4. **Unit test** — test_breaker_state_returns_state_name_not_object_repr

**Verdict:** The BREAK-01 fix is correctly implemented. The `global_breaker=global_config.breaker` argument is now passed to the main curator constructor (line 186), matching the temp curator path (lines 172-173) that was already correct. The duplicate breaker merge code in `curator.py` has been properly removed — `grep -c 'searcher.config.breaker' curator.py` confirms exactly one assignment remains. All targeted tests pass.

**Remaining concerns are quality/maintainability issues** (no correctness bugs found in the breaker wiring or merge logic). The primary quality concern is that there is no mechanism to opt out of circuit breakers — `run_job()` always falls back to `BreakerConfig.defaults()` when no config is provided, which may surprise users.

## Warnings

### WR-01: No circuit breaker opt-out — defaults always applied in run_job()

**File:** `src/biocurator/core/curator.py:183-198`
**Issue:** When neither global nor per-job breaker configs are provided, `run_job()` falls back to `BreakerConfig.defaults()` (fail_max=5, recovery_timeout=60). This means every searcher always gets a circuit breaker, even when the user never opted in. Once tripped (5 failures within the window), all API traffic to that provider is blocked for 60 seconds with no user-facing indication other than breaker state in health checks.

Note: this is pre-existing behavior (not introduced by this phase), but the deduplication made the flow clearer by removing the dead secondary assignment — making the always-on behavior more apparent.

**Fix:** Add an `enabled: bool` field to `BreakerConfig` (default `True`). When `False`, skip breaker creation entirely:
```python
@dataclass
class BreakerConfig:
    enabled: bool = True               # NEW
    fail_max: int | None = None
    recovery_timeout: int | None = None
    half_open_max_successes: int | None = None
```
Then in `_init_breaker()`:
```python
def _init_breaker(self) -> pybreaker.CircuitBreaker | None:
    if self.config.breaker is None or not self.config.breaker.enabled:
        return None
    ...
```

### WR-02: Inconsistent breaker state between preflight and job execution

**File:** `src/biocurator/cli/commands/run.py:169-187`
**Issue:** When `--check` is used, the temp curator (line 170) creates searchers via `_init_database_searchers()` with `breaker=self.global_breaker`. The health check reports breaker state from these searchers. Then `run_job()` (line 236) re-initializes the main curator's searcher breakers with merged configs (global + per-job + defaults). Any breaker state from the preflight (e.g., a breaker that tripped during probing) does NOT propagate to the main curator because the two instances are independent. This is by design but could confuse users if the preflight shows a tripped breaker that silently resets for execution.

**Fix:** Consider documenting this independence in a CLI help string or a preflight informational message. Alternatively, have the main curator re-use the temp curator's searchers to preserve breaker state across the check → execute boundary.

## Info

### IN-01: Redundant local import of `Table` in `_run_preflight_check`

**File:** `src/biocurator/cli/commands/run.py:31`
**Issue:** `Table` is imported at module level (line 16) and again inside `_run_preflight_check` (line 31). The local import is unnecessary and triggers a redundant import resolution. This was likely a copy-paste artifact from when `_run_preflight_check` was prototyped independently before being moved into the module.

**Fix:** Remove line 31 (`from rich.table import Table`). The module-level import on line 16 already covers it.

### IN-02: Redundant null-check for `job_config.search` in run_job()

**File:** `src/biocurator/core/curator.py:189`
**Issue:** `job_config.search` is typed as `SearchConfig` (required, never `None` in the `JobConfig` dataclass). The guard `if job_config.search and job_config.search.breaker` short-circuits correctly, but the first condition is always truthy. This is defensive coding that adds noise without benefit.

**Fix:** Simplify to `if job_config.search.breaker`:
```python
per_db_breaker = (
    job_config.search.breaker.get(db_name)
    if job_config.search.breaker
    else None
)
```

### IN-03: Imprecise return type annotation for `run_job()`

**File:** `src/biocurator/core/curator.py:130`
**Issue:** The return type is annotated as `-> dict` instead of the more precise `-> Dict[str, Path]`. This deprives type checkers and IDE users of specific type information.

**Fix:** Change line 130:
```python
def run_job(self, job_config, progress_callback=None) -> Dict[str, Path]:
```

### IN-04: Duplicate `DatabaseConfig` import in test function

**File:** `tests/providers/test_base.py:141`
**Issue:** `DatabaseConfig` is imported at module level (line 4) and re-imported inside `test_breaker_state_returns_state_name_not_object_repr` (line 141). The inner import is redundant since the symbol is already available in module scope.

**Fix:** Remove line 141 (`from biocurator.providers.base import DatabaseConfig`) and rely on the module-level import.

---

_Reviewed: 2026-05-26_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
