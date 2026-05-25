# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-25)

**Core value:** Reliably download verified biological sequence data from public databases with a single CLI command, even across intermittent network failures.
**Current focus:** Phase 1 — Error Handling & Retry Foundation

## Current Position

Phase: 1 of 5 (Error Handling & Retry Foundation)
Plan: 3 of 3 in current phase
Status: Planned (ready to execute)
Last activity: 2026-05-25 — Phase 1 planning completed

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: N/A
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**
- Last 5 plans: N/A
- Trend: N/A

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- (Roadmap): 5 phases derived from 22 requirements — foundation first, then circuit breaker/health, checksums, CLI commands, integration polish
- (Phase 1 discuss): Global retry defaults (top-level YAML) + per-database overrides in job search config
- (Phase 1 discuss): Collect & report for generator batch errors; raise typed exceptions in search()
- (Phase 1 discuss): Retry only network errors (ConnectionError, Timeout, 5xx); never data/parse errors
- (Phase 1 discuss): Full replacement of custom @retry with tenacity at all 3 call sites
- (Phase 1 discuss): User-friendly config names (max_attempts, backoff_factor, max_delay)

### Pending Todos

None yet.

### Blockers/Concerns

- ERR-01 (fix silent error swallowing) is the absolute prerequisite — every other reliability feature depends on exceptions propagating. Phase 1 must address this first.
- Tenacity migration and narrow exception targeting must be done together — the current `@retry` catches `Exception` broadly, which would undermine the benefit of migrating to tenacity.

## Deferred Items

Items acknowledged and carried forward from previous milestone close:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none)* | | | |

## Session Continuity

Last session: 2026-05-25
Stopped at: Roadmap created, awaiting approval
Resume file: None
