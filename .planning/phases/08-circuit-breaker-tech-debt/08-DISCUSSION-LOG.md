# Phase 08: Circuit Breaker Tech Debt Cleanup — Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-26
**Phase:** 08-circuit-breaker-tech-debt
**Areas discussed:** Preview wiring scope, Test coverage depth, success_threshold verification

---

## Preview Wiring Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Option A — Full wiring | Pass retry+breaker to Biocurator() AND call _init_breaker() for each searcher in _init_database_searchers() | ✓ |
| Option B — Constructor only | Just pass retry+breaker to Biocurator(), no per-searcher breaker init | |

**User's choice:** Option A — Full wiring
**Notes:** Preview searches currently run without breaker protection because __breaker stays None until run_job() sets it. The fix is 2-3 lines of code: pass kwargs to constructor and add _init_breaker() call in _init_database_searchers().

---

## Test Coverage Depth

| Option | Description | Selected |
|--------|-------------|----------|
| Option A — Unit tests only | Mock external APIs (Bio.Entrez, requests), ~6-8 self-contained tests | ✓ |
| Option B — Mix of unit + integration | Unit tests for config/schema, integration test for status command with real APIs | |

**User's choice:** Option A — Unit tests only
**Notes:** Network-dependent integration tests add flakiness without proportional benefit. All success criteria are verifiable at unit level with mocks.

---

## success_threshold Verification

| Option | Description | Selected |
|--------|-------------|----------|
| Option A — Direct unit test | Create BreakerConfig, call _init_breaker(), inspect CircuitBreaker.success_threshold | ✓ |
| Option B — Integration test | Verify through full curator flow with per-db config changes | |

**User's choice:** Option A — Direct unit test
**Notes:** The mapping already exists in code (base.py:141). One test proves the chain: BreakerConfig(half_open_max_successes=N) → resolve() → CircuitBreaker(success_threshold=N).

---

## Agent's Discretion

- Exact test file placement (new files vs inline in existing)
- Mock strategy details (patch vs pytest-mock vs monkeypatch)
- Order of task creation (planner determines based on dependency analysis)
- Whether status_command test goes in new file or extends test_run.py
