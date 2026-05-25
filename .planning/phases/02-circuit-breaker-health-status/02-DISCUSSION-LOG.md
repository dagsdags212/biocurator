# Phase 2: Circuit Breaker & Health Status — Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-25
**Phase:** 02-circuit-breaker-health-status
**Areas discussed:** Breaker Library, Breaker Placement, Health Check Approach, Status CLI Output, Circuit Breaker Config

---

## Breaker Library

| Option | Description | Selected |
|--------|-------------|----------|
| pybreaker | Mature, single dep, all 3 states, exception exclusion, callbacks | ✓ |
| Custom minimal breaker | ~100 lines, full control, no external dep | |
| Wrap tenacity's Retrying | Sentinel approach — different semantics | |

**User's choice:** pybreaker
**Notes:** pybreaker handles open/closed/half-open states, supports `exclude=[...]` for filtering non-retryable exceptions, and has listener callbacks for state change logging.

---

## Breaker Placement

| Option | Description | Selected |
|--------|-------------|----------|
| Wrap searcher public methods | Breaker wraps search()/fetch_metadata()/download() — clean separation from retry | ✓ |
| Wrap the HTTP call (inside retry) | Retry consumes breaker attempts on transient blips | |
| Wrap _safe_* methods | Middle ground — retry handles transients, breaker catches sustained | |

**User's choice:** Wrap searcher public methods
**Notes:** Retry handles transients at HTTP level. Breaker catches sustained failures after retry exhausts.

---

## Health Check Approach

| Option | Description | Selected |
|--------|-------------|----------|
| Lightweight ping | Minimal query, fast, low overhead | ✓ |
| Real search call | Most accurate, hits rate limits, slow | |
| Both: ping first, search on failure | Best accuracy, higher latency on degraded paths | |

**User's choice:** Lightweight ping
**Notes:** NCBI: esearch(db="nuccore", term="a[organism]", retmax=1). UniProt: GET /uniprotkb/search?query=a&size=1. Measure response time in ms.

---

## Status CLI Output

| Option | Description | Selected |
|--------|-------------|----------|
| Simple table | Provider, status, response time, breaker state | ✓ |
| Detailed per-endpoint | Per-method breakdown, more informative but slower | |
| Minimal one-line | Compact, good for pre-flight | |

**User's choice:** Simple table
**Notes:** Rich table with green/yellow/red color coding. Consistent with existing CLI output patterns.

---

## Circuit Breaker Config

| Option | Description | Selected |
|--------|-------------|----------|
| All three knobs | fail_max, recovery_timeout, half_open_max_successes | ✓ |
| Just fail_max + recovery_timeout | Simpler, fewer knobs | |
| Fail_max only | Minimal | |

**User's choice:** All three knobs
**Notes:** Config naming follows Phase 1 pattern. Merge priority: per-db > global > pybreaker defaults.

## Deferred Ideas

- Checkpoint persistence across restarts (v2)
- `--watch` mode for continuous monitoring (v2)
- Pre-flight check integration in Phase 5
