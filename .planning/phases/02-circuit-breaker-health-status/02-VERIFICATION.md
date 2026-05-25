---
phase: 02-circuit-breaker-health-status
verified: 2026-05-25T14:00:00Z
status: gaps_found
score: 3/5 must-haves verified
overrides_applied: 0
gaps:
  - truth: "Circuit breaker state (open/closed/half-open) is visible in status output"
    status: failed
    reason: "breaker_state property returns str(pybreaker state object) which is an unparseable Python object repr like '<pybreaker.CircuitClosedState object at 0x...>' instead of a simple 'closed'/'open'/'half_open' string. The CLI Rich table comparison (bs == \"closed\") never matches, so the status command shows the raw object string when a breaker IS configured."
    artifacts:
      - path: "src/biocurator/providers/base.py"
        issue: "breaker_state property at line 149 returns str(breaker.state) which gives object repr instead of state name"
    missing:
      - "Fix breaker_state to return type(breaker.state).__name__ or map to 'closed'/'open'/'half_open'"
  - truth: "Half-open max retries (half_open_max_successes) configuration takes effect"
    status: failed
    reason: "BreakerConfig.half_open_max_successes is defined in schema but never passed to pybreaker.CircuitBreaker. _init_breaker() in base.py line 134-142 omits success_threshold parameter. The config field is a no-op — pybreaker always defaults to success_threshold=1."
    artifacts:
      - path: "src/biocurator/providers/base.py"
        issue: "_init_breaker() missing success_threshold=resolved.half_open_max_successes"
    missing:
      - "Add success_threshold=resolved.half_open_max_successes to the pybreaker.CircuitBreaker() call in _init_breaker()"
  - truth: "Per-database breaker configuration overrides global and activates"
    status: failed
    reason: "run_job() merge logic sets searcher.config.breaker to a merged BreakerConfig, but the searcher's _breaker (pybreaker CircuitBreaker instance) was already created during __init__(). When global_breaker is None, _breaker is None permanently — the merge never recreates the pybreaker instance. Per-database breaker configs never activate."
    artifacts:
      - path: "src/biocurator/core/curator.py"
        issue: "run_job() merge logic at lines 174-188 sets searcher.config.breaker but doesn't call _init_breaker() to recreate the pybreaker instance"
    missing:
      - "After setting searcher.config.breaker = merged, call searcher._breaker = searcher._init_breaker() to recreate the pybreaker CircuitBreaker with the merged config"
deferred: []
human_verification: []
---

# Phase 02: Circuit Breaker & Health Status Verification Report

**Phase Goal:** Circuit breakers prevent cascading failures when a server is down; users can probe provider health via CLI and see breaker state
**Verified:** 2026-05-25T14:00:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | When a provider server is unreachable, circuit breaker opens after configured failure threshold and subsequent calls fail fast | ✓ PARTIAL | Works with global breaker (init-time config). Fails when only per-database breaker is configured (merge bug — `_breaker` stays None). |
| 2 | `biocurator status` probes all configured providers and reports per-provider health with response times | ✓ VERIFIED | HealthChecker.ping_ncbi(), ping_uniprot() work; status command renders Rich table with Provider, Status, Response Time columns |
| 3 | Circuit breaker state (open/closed/half-open) is visible in `biocurator status` output | ✗ FAILED | `breaker_state` returns `str(breaker.state)` which gives `<pybreaker.CircuitClosedState object at 0x...>` — CLI can never match `bs == "closed"`. Falls through to raw object display. |
| 4 | After circuit opens, a recovery probe is automatically attempted after the configured recovery timeout (half-open state) | ✓ VERIFIED | pybreaker handles this natively via `reset_timeout` and `success_threshold` |
| 5 | Circuit breaker configuration (failure threshold, recovery timeout, half-open max retries) is in DatabaseConfig with sensible defaults | ✓ PARTIAL | BreakerConfig exists with all 3 fields + sensible defaults. But `half_open_max_successes` never reaches pybreaker (missing `success_threshold` param). |

**Score:** 3/5 truths verified

### Deferred Items

None — all gaps should be fixed within this phase.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/biocurator/config/schema.py` | BreakerConfig dataclass | ✓ VERIFIED | fail_max, recovery_timeout, half_open_max_successes fields + resolve()/defaults()/from_dict() |
| `src/biocurator/providers/health.py` | HealthChecker with ping_ncbi, ping_uniprot | ✓ VERIFIED | Exists, proper static methods |
| `src/biocurator/providers/base.py` | DatabaseSearcher._init_breaker(), breaker_state | ✓ VERIFIED | Methods exist, pybreaker imported |
| `src/biocurator/providers/ncbi/searcher.py` | Breaker wrapping in search/fetch_metadata/download | ✓ VERIFIED | self._breaker init, breaker.call() in all 3 public methods |
| `src/biocurator/providers/uniprot/searcher.py` | Breaker wrapping in search/fetch_metadata/download | ✓ VERIFIED | self._breaker init, breaker.call() in all 3 public methods |
| `src/biocurator/core/curator.py` | global_breaker param, get_health_status(), merge logic | ✓ VERIFIED | Method exists, merge logic present |
| `src/biocurator/cli/commands/status.py` | status_command with Rich table | ✓ VERIFIED | File exists, proper implementation |
| `src/biocurator/cli/main.py` | status command registration | ✓ VERIFIED | app.command("status")(status_command) |
| `pyproject.toml` | pybreaker dependency | ✓ VERIFIED | pybreaker>=1.4,<2.0 at line 39 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `Biocurator.__init__` | NCBISearcher/UniProtSearcher | `_init_database_searchers()` → `DatabaseConfig(breaker=...)` | ✓ WIRED | BreakerConfig passed to searchers |
| NCBISearcher/UniProtSearcher | pybreaker.CircuitBreaker | `self._init_breaker()` → `pybreaker.CircuitBreaker(...)` | ⚠️ PARTIAL | Missing `success_threshold` param |
| `run_job()` | `searcher.config.breaker` | Merge: per-db > global > defaults | ⚠️ PARTIAL | Config updated but `_breaker` not recreated |
| `get_health_status()` | HealthChecker | `HealthChecker.ping_ncbi()` / `ping_uniprot()` | ✓ WIRED | Static methods called correctly |
| `breaker_state` property | CLI status display | `get_health_status() → s["breaker_state"]` | ✗ NOT_WIRED | Returns unparseable object repr |
| `status_command` | main.py app | `app.command("status")` | ✓ WIRED | Properly registered |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|-------------------|--------|
| `breaker_state` property | `breaker.state` | pybreaker.CircuitBreaker instance | ✓ Yes, but formatted incorrectly | ⚠️ STATIC (wrong format — object repr instead of state name) |
| `get_health_status()` | HealthChecker ping results | Real HTTP calls to NCBI/UniProt | ✓ Yes — real probe data | ✓ FLOWING |
| `run_job()` breaker merge | `searcher.config.breaker` | `BreakerConfig.resolve()` from per-db or global config | ✓ Yes, but `_breaker` not recreated | ✗ DISCONNECTED |
| `_init_breaker()` | pybreaker params | `BreakerConfig.resolve()` | ⚠️ Partial — `half_open_max_successes` dropped | ✗ HOLLOW |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Status command exists | `uv run biocurator status --help` | Help text displayed with --config option | ✓ PASS |
| Backward compatibility | `ConfigLoader.load(valid_config.yaml)` | Global breaker = None, backward compatible | ✓ PASS |
| BreakerCircuit created with global config | `Biocurator('t@t.com', global_breaker=BreakerConfig(fail_max=5))` | Searchers have pybreaker.CircuitBreaker objects | ✓ PASS |
| Get health status shape | `Biocurator.get_health_status()` | Returns list of dicts with correct keys | ✓ PASS |
| Breaker state string format | `str(searcher.breaker_state)` | Returns unparseable `<pybreaker.CircuitClosedState object at 0x...>` | ✗ FAIL |
| Breaker merge with per-db override | `run_job()` merge logic | `config.breaker` updated but `_breaker` stays None | ✗ FAIL |
| `success_threshold` in breaker init | Check `_init_breaker()` source | Missing — `half_open_max_successes` not passed | ✗ FAIL |
| All tests pass | `uv run pytest tests/ -x -q` | 154 passed in 0.42s | ✓ PASS |

### Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| CB-01 | Per-provider circuit breaker prevents cascading failures | ✗ PARTIAL | Works with global breaker. Fails when only per-db breaker configured (Bug 2 — merge doesn't recreate pybreaker instance). |
| CB-02 | Integrate breaker with searcher public methods | ✓ SATISFIED | search(), fetch_metadata(), download() wrapped with `self._breaker.call()` in both NCBI and UniProt searchers |
| CB-03 | Breaker config in DatabaseConfig — failure threshold, recovery timeout, half-open max retries | ✗ PARTIAL | BreakerConfig fields exist. But `half_open_max_successes` never reaches pybreaker (Bug 1 — missing `success_threshold` in `_init_breaker()`). |
| CB-04 | Expose breaker state for observability | ✗ BLOCKED | `breaker_state` property exists but returns unparseable object repr. CLI display of breaker state broken. |
| STATUS-01 | HealthChecker probes NCBI and UniProt | ✓ SATISFIED | `ping_ncbi()` and `ping_uniprot()` static methods with timeout handling |
| STATUS-02 | `biocurator status` command | ✓ SATISFIED | Command exists, registers as `biocurator status`, probes all configured providers |
| STATUS-03 | Show breaker state in status output | ✗ BLOCKED | Breaker State column exists but displays `<pybreaker.CircuitClosedState object at 0x...>` instead of "closed"/"open"/"half_open" |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/biocurator/providers/base.py` | 138-142 | Missing `success_threshold` in pybreaker.CircuitBreaker constructor | 🛑 BLOCKER | `half_open_max_successes` config is a no-op; user-configured value never takes effect |
| `src/biocurator/providers/base.py` | 149 | `str(breaker.state)` returns Python object repr, not state name | 🛑 BLOCKER | CLI status command shows `<pybreaker.CircuitClosedState object at 0x...>` instead of "closed" |
| `src/biocurator/core/curator.py` | 174-188 | Merge sets config.breaker but doesn't recreate `_breaker` property | 🛑 BLOCKER | Per-database breaker overrides never activate; breakers don't work when only per-db breaker configured without global |

### No Tests for Circuit Breaker or Health Check Functionality

| Issue | Impact |
|-------|--------|
| No tests for `BreakerConfig` dataclass (resolve/defaults/from_dict) | Config merge logic untested |
| No tests for `_init_breaker()` method | Wrong params not caught |
| No tests for `breaker_state` property | Wrong format not caught |
| No tests for `HealthChecker.ping_ncbi()`/`ping_uniprot()` | Probe methods untested |
| No tests for `get_health_status()` | Method not covered |
| No tests for `status_command` | CLI behavior not tested |

The 154 existing tests all pass because they were written before Phase 02 and don't exercise any new functionality.

### Gaps Summary

**3 blocking bugs found in Phase 02 implementation:**

1. **BUG 1 (Missing `success_threshold` parameter):** `DatabaseSearcher._init_breaker()` at `src/biocurator/providers/base.py:138-142` creates a `pybreaker.CircuitBreaker` with only `fail_max`, `reset_timeout`, and `exclude`. The `success_threshold` parameter is never passed, so `BreakerConfig.half_open_max_successes` is silently ignored. Users can configure `half_open_max_successes` but it never takes effect — pybreaker always defaults to 1.

2. **BUG 2 (Merge doesn't recreate pybreaker instance):** `Biocurator.run_job()` at `src/biocurator/core/curator.py:174-188` applies breaker merge logic (per-db > global > defaults) by assigning to `searcher.config.breaker`. However, the searcher's `_breaker` attribute (the actual `pybreaker.CircuitBreaker` instance) was already created (or not) during `__init__()`. The merge never calls `_init_breaker()` again, so:
   - When `global_breaker=None`: `_breaker` stays None even after merge, so breaker wrapping never activates
   - When `global_breaker` is set: `_breaker` is created at init with initial config; per-db overrides in job config are ignored

3. **BUG 3 (`breaker_state` returns unparseable Python object repr):** `DatabaseSearcher.breaker_state` property at `src/biocurator/providers/base.py:149` returns `str(breaker.state)`. Since pybreaker state objects don't define `__str__`, this returns `<pybreaker.CircuitClosedState object at 0x...>`. The CLI status command at `src/biocurator/cli/commands/status.py:73-81` compares against `"closed"`/`"half_open"`/`"open"`, which never matches. Breaker state display shows the ugly object repr instead.

**What already works:**
- `BreakerConfig` dataclass with all fields, resolve/defaults/from_dict methods ✓
- YAML parsing of global and per-database breaker blocks ✓
- HealthChecker with ping_ncbi() and ping_uniprot() ✓
- `biocurator status` command with Rich table (Provider, Status, Response Time columns) ✓
- Global breaker configuration at init time ✓
- Breaker wrapping of all 3 public methods in both searchers ✓
- `get_health_status()` method returning per-provider health ✓
- Backward compatibility with existing config files ✓
- pybreaker dependency in pyproject.toml ✓

**What needs fixing (in priority order):**
1. Fix `breaker_state` property to return state name (e.g., `"closed"`, `"open"`, `"half_open"`)
2. Add `success_threshold=resolved.half_open_max_successes` to `_init_breaker()` pybreaker.CircuitBreaker call
3. Add `searcher._breaker = searcher._init_breaker()` after the config merge in `run_job()`

---

_Verified: 2026-05-25T14:00:00Z_
_Verifier: Claude (gsd-verifier)_
