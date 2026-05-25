---
phase: 07-circuit-breaker-critical-fixes
plan: 01
subsystem: reliability
tags: [pybreaker, circuit-breaker, typer]

# Dependency graph
requires: []
provides:
  - global_breaker wiring to main curator in run.py (BREAK-01 fix)
  - Deduplicated breaker merge logic in curator.py run_job()
  - Regression test for global_breaker constructor wiring
  - Unit test for breaker_state returning state.name string
affects: [status, run]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "TDD regression test pattern: patch Biocurator class, assert mock_cls.call_args[1][\"global_breaker\"] to verify constructor wiring"

key-files:
  created: []
  modified:
    - src/biocurator/cli/commands/run.py
    - src/biocurator/core/curator.py
    - tests/cli/test_run.py
    - tests/providers/test_base.py

key-decisions:
  - "No architectural changes — minimal fix to pass existing global_config.breaker through to main curator constructor, matching temp curator path"

patterns-established:
  - "CLI-to-curator constructor wiring regression: use patch with mock_cls.call_args[1] to assert kwargs reach the constructor"

requirements-completed: [CB-04, STATUS-03]

# Metrics
duration: 5min
completed: 2026-05-26
---

# Phase 07 Plan 01: Circuit Breaker Critical Fixes Summary

**Fix BREAK-01 global_breaker wiring gap, deduplicate breaker merge code, and add regression tests for CB-04/STATUS-03 display chain**

## Performance

- **Duration:** ~5 min
- **Tasks:** 3
- **Files modified:** 4
- **Total tests:** 192 passed (191 existing + 1 new)

## Accomplishments

- BREAK-01 fixed: main curator in `run.py:183` now receives `global_breaker=global_config.breaker` matching the temp curator path at line 170
- Duplicate breaker merge code at `curator.py:199-208` removed — `grep -c 'searcher.config.breaker'` now returns 1
- Regression test `test_run_main_curator_receives_global_breaker` verifies constructor receives BreakerConfig with `fail_max=3`
- Unit test `test_breaker_state_returns_state_name_not_object_repr` confirms `breaker_state` returns `'closed'/'open'/'half_open'` strings matching display logic in `status.py` and `run.py`

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Add failing regression test** — `1981c7d` (test)
2. **Task 1 (GREEN): Fix global_breaker wiring** — `21168ee` (feat)
3. **Task 2: Remove duplicate breaker merge** — `612386b` (refactor)
4. **Task 3: Add breaker_state unit test** — `794a2fd` (test)

## Files Created/Modified

- `src/biocurator/cli/commands/run.py` — Added `global_breaker=global_config.breaker` to main curator constructor (line 186)
- `src/biocurator/core/curator.py` — Removed duplicate breaker merge lines (199-208), single assignment remains at line 193
- `tests/cli/test_run.py` — Added `test_run_main_curator_receives_global_breaker` regression test
- `tests/providers/test_base.py` — Added `test_breaker_state_returns_state_name_not_object_repr` unit test

## Decisions Made

None — followed plan as specified. All three issues were already diagnosed in the plan context.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Circuit breaker wiring gap is closed: circuit breakers are now active on all curator paths
- `breaker_state` returns human-readable strings consumed by `status` and `run --check` display logic
- Full test suite (192 tests) passes with no regressions

---

*Phase: 07-circuit-breaker-critical-fixes*
*Completed: 2026-05-26*
