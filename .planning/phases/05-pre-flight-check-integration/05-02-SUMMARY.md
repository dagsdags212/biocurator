---
phase: 05-pre-flight-check-integration
plan: 02
subsystem: cli
tags: [typer, rich, circuit-breaker, health-check, cli]

# Dependency graph
requires:
  - phase: 05-pre-flight-check-integration
    plan: 01
    provides: "SearchConfig.preflight_check field, ConfigLoader._parse_job() preflight_check parsing"
provides:
  - "--check/--no-check CLI flags on biocurator run"
  - "Pre-flight provider health check rendered as Rich table before job execution"
  - "Interactive proceed/abort prompt when providers are unreachable"
  - "CLI flag override for config file's preflight_check setting"
affects: [status, run]

# Tech tracking
tech-stack:
  added: []
  patterns: 
    - "CLI flag overrides config toggle pattern: --check/--no-check > search.preflight_check"
    - "Temporary curator for health probes: lightweight Biocurator instance discarded after check"
    - "Inline Rich console.print() instead of utility functions (avoid circular import)"
    - "Rich Confirm.ask() for interactive prompts with safe non-TTY default (False)"

key-files:
  created: []
  modified:
    - src/biocurator/cli/commands/run.py
    - tests/cli/test_run.py

key-decisions:
  - "--check/--no-check uses Optional[bool] (None=use config, True=always, False=never)"
  - "Pre-flight creates a temporary Biocurator instance for health probes, separate from job execution"
  - "Health table format matches biocurator status exactly for consistent UX"
  - "Confirm.ask() default=False — safe for non-interactive TTYs"

patterns-established:
  - "Pre-flight check pattern: probe → render table → prompt → proceed/abort"
  - "CLI flag precedence over config: explicit flag always wins over file setting"

requirements-completed: [STATUS-04]

# Metrics
duration: 3min
completed: 2026-05-25
---

# Phase 5 Plan 2: Pre-Flight Check CLI Integration Summary

**`biocurator run --check` probes provider health via Rich table with interactive proceed/abort prompt before job execution**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-05-25T18:07:17Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments
- Added `--check`/`--no-check` CLI flags to `biocurator run` command with `Optional[bool]` default None
- Implemented `_run_preflight_check()` helper that probes all providers, renders a Rich health table, and prompts user proceed/abort
- Wired pre-flight logic into run_command: CLI flag overrides config `preflight_check` toggle, temp Biocurator for probes
- All providers UP → job proceeds automatically without interruption (no prompt)
- Provider DOWN → warning displayed, "Proceed anyway?" with safe default No, exit code 1 on abort
- `--no-check` bypasses pre-flight entirely even if `preflight_check: true` is in config

## Task Commits

1. **Task 1: Add --check and --no-check flags to run_command** - `b12781e` (feat)
2. **Task 2: Implement pre-flight health check logic in run_command** - `4d0e011` (feat)
3. **Task 3: Add tests for run --check and pre-flight flow** - `bbb2060` (test)

## Files Created/Modified
- `src/biocurator/cli/commands/run.py` - Added --check/--no-check flag, `_run_preflight_check()` helper, pre-flight wiring with do_preflight logic and temp curator
- `tests/cli/test_run.py` - Added 4 tests (all UP proceeds, DOWN abort exits, DOWN proceed continues, --no-check skips)

## Decisions Made
- `Optional[bool]` for check parameter: None = use config, True = always, False = never — clean tri-state without custom enums
- Temporary Biocurator instance for health probes: avoids coupling health checks to job execution curator, both use same `email`, `retry`, and `breaker` config
- Health table format matches `biocurator status` exactly: same columns, same color coding, same header style for consistent UX
- `Confirm.ask(default=False)`: safe for non-interactive TTYs (piped input, CI, etc.) — aborts by default

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None — all edits applied cleanly, all tests passed on first run.

## Next Phase Readiness
- All CLI pre-flight integration complete for STATUS-04 requirement
- `biocurator run --check` now provides confidence before long-running curation jobs
- All 190 tests pass with no regressions across retry, circuit breaker, health checks, manifests, and CLI commands

---
*Phase: 05-pre-flight-check-integration*
*Completed: 2026-05-25*
