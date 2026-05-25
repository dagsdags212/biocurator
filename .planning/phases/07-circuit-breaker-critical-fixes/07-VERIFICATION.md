---
phase: 07-circuit-breaker-critical-fixes
verified: 2026-05-26T00:00:00Z
status: passed
score: 3/3 must-haves verified
overrides_applied: 0
---

# Phase 7: Circuit Breaker Critical Fixes — Verification Report

**Phase Goal:** "Fix three blocking bugs found by the milestone audit — breaker_state returns object repr, main curator loses global_breaker, and status display is broken"
**Verified:** 2026-05-26
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Circuit breakers are active when biocurator run executes without --check | ✓ VERIFIED | `run.py:183-187` passes `global_breaker=global_config.breaker` to the main `Biocurator()` constructor, matching the temp_curator path at `run.py:170-174`. `curator.py:_init_database_searchers()` propagates it to `DatabaseConfig(breaker=self.global_breaker)`. `run_job()` at `curator.py:198` calls `searcher._breaker = searcher._init_breaker()`, creating the actual `pybreaker.CircuitBreaker`. |
| 2 | breaker_state property returns human-readable 'closed'/'open'/'half_open' | ✓ VERIFIED | `base.py:149-154` returns `breaker.state.name` — a string, not a Python object repr. Behavioral spot-check confirms actual return value is `'closed'` (type `str`). |
| 3 | biocurator status displays color-coded breaker state names | ✓ VERIFIED | `status.py:72-82` compares `bs` against `"closed"`, `"half_open"`, `"open"` strings with Rich color markup. `run.py:54-64` has identical color-coded display for pre-flight health check table. Both match the strings returned by `pybreaker.CircuitBreaker.state.name`. |

**Score:** 3/3 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/biocurator/cli/commands/run.py` | Main curator global_breaker wiring | ✓ VERIFIED | `global_breaker=global_config.breaker` at line 186 (exactly 2 total matches: lines 173 + 186). Exists, substantive, wired. |
| `src/biocurator/core/curator.py` | Deduplicated breaker merge logic | ✓ VERIFIED | Single `searcher.config.breaker` assignment at line 193. `grep -c` returns 1. Duplicate lines 199-208 removed. |
| `tests/cli/test_run.py` | Regression test for global_breaker wiring | ✓ VERIFIED | `test_run_main_curator_receives_global_breaker` at line 180. Creates config with breaker, patches Biocurator, asserts `call_args[1]["global_breaker"].fail_max == 3`. 192 tests pass. |
| `tests/providers/test_base.py` | Unit test for breaker_state returning state.name | ✓ VERIFIED | `test_breaker_state_returns_state_name_not_object_repr` at line 138. Creates NCBISearcher with BreakerConfig, asserts `breaker_state` is in `("closed", "open", "half_open")`. 192 tests pass. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `run.py:186` | `Biocurator.__init__ global_breaker param` | `global_breaker=global_config.breaker` | ✓ WIRED | Constructor receives `global_breaker` kwarg; `_init_database_searchers()` passes it to `DatabaseConfig(breaker=self.global_breaker)`; `_init_breaker()` creates `pybreaker.CircuitBreaker`; `run_job()` calls `searcher._breaker = searcher._init_breaker()`. Full chain: config → CLI → constructor → DatabaseConfig → pybreaker CircuitBreaker. |
| `base.py:154` | `status.py` / `run.py` breaker state display | `breaker.state.name → 'closed'/'open'/'half_open'` | ✓ WIRED | `breaker_state` property returns `breaker.state.name` (string). `get_health_status()` at `curator.py:98-100` reads it. `status.py:72-82` and `run.py:54-64` compare against same string values with Rich color markup. pybreaker convention matches: `state.name` is always one of `"closed"`, `"open"`, `"half_open"`. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `run.py:183-187` (main curator) | `global_config.breaker` | `ConfigLoader.load(config)` → `GlobalConfig.breaker` | ✓ Real | YAML config parsed into `BreakerConfig` dataclass (confirmed by test). |
| `curator.py:68,79` (DatabaseConfig) | `self.global_breaker` | `__init__` parameter → `DatabaseConfig(breaker=...)` | ✓ Real | Propagated to searcher config, consumed by `_init_breaker()`. |
| `base.py:154` (breaker_state) | `breaker.state.name` | `pybreaker.CircuitBreaker.state` (pybreaker internals) | ✓ Real | Returns `'closed'` on fresh breaker (spot-check confirmed). |
| `status.py:72-82` (display) | `s["breaker_state"]` | `curator.get_health_status()` → `searcher.breaker_state` | ✓ Real | String values compared for color-coded Rich display. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| breaker_state returns string (not object repr) | `python -c "NCBISearcher(..., BreakerConfig(...)).breaker_state"` | `'closed'` (type `str`) | ✓ PASS |
| pybreaker state.name values match display comparisons | `python -c "pybreaker.CircuitBreaker().state.name"` | `'closed'` — matches `== "closed"` in status.py/run.py | ✓ PASS |
| Full test suite passes | `uv run pytest tests/ -x -q` | `192 passed in 0.50s` | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| CB-04 | 07-01-PLAN | Expose circuit breaker state for observability (CLI status command and logs) | ✓ SATISFIED | `base.py:154` returns `breaker.state.name` (string); `status.py:72-82` and `run.py:54-64` display color-coded breaker state; unit test at `tests/providers/test_base.py:138` confirms. |
| STATUS-03 | 07-01-PLAN | Show circuit breaker state in status output (open/closed/half-open counts) | ✓ SATISFIED | `status.py:72-82` renders color-coded breaker state per provider in a Rich table; `run.py:54-64` does the same for pre-flight health check. Both compare against `"closed"`, `"half_open"`, `"open"` strings from `pybreaker`. |

**No orphaned requirements.** Only CB-04 and STATUS-03 are mapped to Phase 7 in REQUIREMENTS.md; both are claimed by PLAN frontmatter.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | — | — | None found in modified files |

`TBD`/`FIXME`/`XXX` scan: zero matches across all four modified files.
Stub/placeholder scan: zero matches in implementation code (`tests/providers/test_base.py` returns `[]` in a test-only `_Concrete` ABC subclass — intentional minimal abstract method implementation for unit testing, not a stub).

### Human Verification Required

None. All three observable truths are programmatically verifiable:
- Truth 1: grep confirms constructor wiring + regression test passes
- Truth 2: source code inspection + behavioral spot-check + unit test
- Truth 3: source code inspection matches pybreaker convention + manual test confirmed string value

## Gaps Summary

No gaps found. All three blocking bugs are fixed:

1. **BREAK-01 (main curator loses global_breaker):** Fixed at `run.py:186`. Regression test `test_run_main_curator_receives_global_breaker` verifies the constructor receives the `global_breaker` kwarg with correct `fail_max` value.

2. **breaker_state returns object repr:** Already fixed before this phase (`base.py:154` returns `breaker.state.name`). Unit test `test_breaker_state_returns_state_name_not_object_repr` confirms string output.

3. **Duplicate breaker merge code:** Removed from `curator.py` (lines 199-208 deleted). `grep -c 'searcher.config.breaker'` confirms single assignment remains.

---

_Verified: 2026-05-26_
_Verifier: Claude (gsd-verifier)_
