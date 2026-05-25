---
phase: 02-circuit-breaker-health-status
plan: 01
subsystem: config
tags: [circuit-breaker, pybreaker, config, yaml-parsing]

requires:
  - phase: 01-error-handling-retry
    provides: RetryConfig pattern, ConfigLoader YAML parsing structure, DatabaseConfig fields
provides:
  - BreakerConfig dataclass with resolve/defaults/from_dict methods
  - breaker field on DatabaseConfig for per-provider circuit breaker configuration
  - breaker fields on SearchConfig (per-database overrides) and GlobalConfig (defaults)
  - YAML parsing of global and per-database breaker blocks in ConfigLoader
  - pybreaker dependency for downstream circuit breaker integration
affects: [02-02, 02-03]

tech-stack:
  added:
    - pybreaker>=1.4,<2.0
  patterns:
    - BreakerConfig follows RetryConfig pattern (None sentinel, resolve(), from_dict(), defaults())
    - Config merge priority: per-database override > global > pybreaker defaults

key-files:
  created: []
  modified:
    - pyproject.toml
    - src/biocurator/config/schema.py
    - src/biocurator/providers/base.py
    - src/biocurator/config/loader.py

key-decisions:
  - "pybreaker version pinned >=1.4,<2.0 (not >=2.0 as originally planned — 1.4.1 is latest available)"
  - "BreakerConfig docstring maps half_open_max_successes to pybreaker's success_threshold (not max_retry, which doesn't exist in pybreaker 1.x)"
  - "breaker fields default to None everywhere to preserve backward compatibility with existing YAML configs"

patterns-established:
  - "Config dataclass patterns: None defaults, resolve() for merge, from_dict() for YAML parsing, defaults() for pybreaker defaults"
  - "ConfigLoader parsing pattern: global block at top-level, per-database dict in search section"

requirements-completed:
  - CB-01
  - CB-03
  - CFG-02

duration: 12min
completed: 2026-05-25
---

# Phase 02 Circuit Breaker Plan 01: BreakerConfig Foundation Summary

**BreakerConfig dataclass with pybreaker dependency, DatabaseConfig integration, and YAML config parsing for per-provider circuit breaker settings**

## Performance

- **Duration:** 12 min
- **Started:** 2026-05-25T09:39:00Z
- **Completed:** 2026-05-25T09:51:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Added pybreaker>=1.4,<2.0 as a project dependency (resolved: 1.4.1) and locked via uv.lock
- Created BreakerConfig dataclass with fail_max, recovery_timeout, half_open_max_successes fields following RetryConfig pattern
- Added breaker field to DatabaseConfig in providers/base.py for per-provider circuit breaker config
- Added breaker fields to SearchConfig (per-database overrides) and GlobalConfig (global defaults) in schema.py
- Implemented YAML parsing for breaker blocks in ConfigLoader._parse() (global) and _parse_job() (per-database)
- All 154 existing tests pass — fully backward compatible

## Task Commits

1. **Task 1: Add pybreaker dependency and BreakerConfig dataclass** — `3a0369f` (feat)
2. **Task 2: Add BreakerConfig to DatabaseConfig and parse breaker blocks from YAML** — `2d6727d` (feat)

## Files Created/Modified

- `pyproject.toml` — Added pybreaker>=1.4,<2.0 dependency
- `src/biocurator/config/schema.py` — Added BreakerConfig dataclass (after RetryConfig), breaker field on SearchConfig + GlobalConfig
- `src/biocurator/providers/base.py` — Added BreakerConfig import and breaker field on DatabaseConfig
- `src/biocurator/config/loader.py` — Added BreakerConfig import, global breaker parsing in _parse(), per-database breaker overrides in _parse_job()

## Decisions Made

- **pybreaker version pinned >=1.4,<2.0**: The plan specified >=2.0,<3.0 but pybreaker's latest release is 1.4.1. Adjusted constraint to match available versions.
- **half_open_max_successes maps to success_threshold**: pybreaker 1.4.1 uses `success_threshold` (not `max_retry` as originally guessed). The docstring reflects the correct mapping.
- **Backward compatible defaults**: All breaker fields default to None, matching the RetryConfig pattern. Existing YAML configs without breaker blocks parse identically.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed pybreaker version constraint**
- **Found during:** Task 1 (pyproject.toml update)
- **Issue:** `pybreaker>=2.0,<3.0` couldn't resolve — pybreaker's latest release is 1.4.1, not 2.0
- **Fix:** Changed constraint to `pybreaker>=1.4,<2.0`
- **Files modified:** pyproject.toml
- **Verification:** `uv sync` succeeds, pybreaker imports cleanly with `from pybreaker import CircuitBreaker`
- **Committed in:** 3a0369f (Task 1 commit)

**2. [Rule 1 - Bug] Fixed BreakerConfig pybreaker mapping in docstring**
- **Found during:** Task 1 (BreakerConfig implementation)
- **Issue:** Plan's docstring mapped `half_open_max_successes` to `max_retry` — pybreaker 1.4.1 uses `success_threshold`
- **Fix:** Updated docstring to map `half_open_max_successes -> success_threshold`
- **Files modified:** src/biocurator/config/schema.py
- **Verification:** Verified pybreaker.CircuitBreaker init signature shows `success_threshold: 1`
- **Committed in:** 3a0369f (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (Rule 1)
**Impact on plan:** Both fixes necessary for correctness. No scope creep.

## Issues Encountered

None — both deviations were auto-fixed via Rule 1 during Task 1 execution. Task 2 executed exactly as planned.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- BreakerConfig foundation complete, ready for Plans 02-02 and 02-03
- Plan 02-02 can integrate pybreaker.CircuitBreaker into the provider layer (CB-02 requirement)
- Plan 02-03 can expose circuit breaker state for observability (CB-04 requirement)
- Config merge logic (per-database > global > pybreaker defaults) is established via BreakerConfig.resolve()

---
*Phase: 02-circuit-breaker-health-status*
*Completed: 2026-05-25*
