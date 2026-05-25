# Roadmap: Biocurator

## Overview

Take a working-but-fragile bioinformatics CLI tool (silent error swallowing, custom retry, no data integrity) and harden it with proper reliability patterns — configurable retry via tenacity, per-provider circuit breakers, health checks, SHA-256 checksums, job manifests, and CLI commands for visibility. Each phase delivers a user-observable capability from the fix of silent failures through pre-flight health checks.

## Phases

- [ ] **Phase 1: Error Handling & Retry Foundation** - Fix silent error swallowing, migrate to tenacity retry, add per-provider retry config to schema
- [x] **Phase 2: Circuit Breaker & Health Status** - Per-provider circuit breakers, `biocurator status` command with health probes and breaker state (completed 2026-05-25)
- [x] **Phase 3: Checksums & Manifests** - SHA-256 checksums during streaming export, per-job manifest files with provenance metadata (completed 2026-05-25)
- [x] **Phase 4: CLI Jobs & Files Commands** - `biocurator jobs`, `biocurator files`, and `files --verify` for data integrity verification (completed 2026-05-26)
- [x] **Phase 5: Pre-flight Check & Integration** - `biocurator run --check`, config pre-flight toggle, end-to-end reliability integration (planned 2026-05-26)
- [ ] **Phase 6: Retrospective Verification (Phase 01 & 04)** - Create VERIFICATION.md for Phases 01 and 04 (gap closure)
- [ ] **Phase 7: Circuit Breaker Critical Fixes** - Fix breaker_state repr, global_breaker wiring, STATUS-03 display (gap closure)
- [ ] **Phase 8: Circuit Breaker Tech Debt Cleanup** - Fix success_threshold, merge+recreate breaker, test coverage, preview curator (gap closure)
- [ ] **Phase 9: Checksums Code Review Fixes** - Fix CR-01 through CR-05 from Phase 03 review (gap closure)
- [ ] **Phase 10: Cleanup & Polish** - Delete orphaned utils/network.py, complete Phase 05 human UAT (gap closure)

## Phase Details

### Phase 1: Error Handling & Retry Foundation
**Goal**: Exceptions propagate clearly instead of silent empty results; retry uses tenacity with configurable per-provider settings; config schema accepts all new fields
**Depends on**: Nothing (first phase)
**Requirements**: ERR-01, ERR-02, ERR-03, ERR-04, CFG-01, CFG-02
**Success Criteria** (what must be TRUE):
  1. User sees clear exception messages with traceback when NCBI/UniProt API calls fail — never silent `return []`
  2. User can configure retry parameters (`max_attempts`, `backoff_factor`, `timeout`) per provider in config YAML
  3. Existing YAML configs without the new retry/breaker/timeout fields parse without error (backward compatible)
  4. Retry uses tenacity; log messages show retry attempt numbers with backoff timing
  5. Typed exceptions distinguish network errors (transient, retryable) from data/parse errors (permanent, not retryable)
**Plans**: 3 plans in 2 waves

Plans:
- [ ] 01-01-PLAN.md — Config Foundation + Utility Setup (RetryConfig, schema, loader, retryable_exceptions, network.py gut)
- [ ] 01-02-PLAN.md — NCBI Searcher Migration + Retry Merge (tenacity, narrow exceptions, DatabaseSearchError, merge logic)
- [ ] 01-03-PLAN.md — UniProt Searcher Migration + Tests (tenacity, narrow exceptions, RetryConfig tests)

### Phase 2: Circuit Breaker & Health Status
**Goal**: Circuit breakers prevent cascading failures when a server is down; users can probe provider health via CLI and see breaker state
**Depends on**: Phase 1
**Requirements**: CB-01, CB-02, CB-03, CB-04, STATUS-01, STATUS-02, STATUS-03
**Success Criteria** (what must be TRUE):
  1. When a provider server is unreachable, circuit breaker opens after configured failure threshold and subsequent calls fail fast (no timeout wait)
  2. `biocurator status` probes all configured providers and reports per-provider health (reachable/unreachable) with response times
  3. Circuit breaker state (open/closed/half-open) is visible in `biocurator status` output
  4. After circuit opens, a recovery probe is automatically attempted after the configured recovery timeout (half-open state)
  5. Circuit breaker configuration (failure threshold, recovery timeout, half-open max retries) is in `DatabaseConfig` with sensible defaults
**Plans**: 3 plans in 3 waves

Plans:
- [x] 02-01-PLAN.md — BreakerConfig Foundation (config schema, pybreaker, loader parsing)
- [x] 02-02-PLAN.md — Circuit Breaker + HealthChecker Integration (searcher wrapping, HealthChecker, curator wiring)
- [x] 02-03-PLAN.md — biocurator status CLI Command (Rich table, health probes, breaker state display)

### Phase 3: Checksums & Manifests
**Goal**: Every downloaded sequence file has a SHA-256 checksum; per-job manifest files track checksums, record counts, and provenance metadata
**Depends on**: Phase 1
**Requirements**: DI-01, DI-02, DI-03, DI-04
**Success Criteria** (what must be TRUE):
  1. Every downloaded sequence file has a SHA-256 checksum generated during streaming export (computed incrementally with `hashlib`)
  2. Per-job manifest JSON file is created in the output directory with checksums, record counts, timestamps, provider, and source URLs
  3. Manifest includes a snapshot of the job config for provenance tracking
  4. Verification function can re-read completed files from disk, recompute SHA-256 checksums, and compare against manifest entries
  5. Manifest format follows BagIt-compatible conventions (verifiable with standard `sha256sum -c`)
**Plans**: 2 plans in 1 wave

Plans:
- [x] 03-01-PLAN.md — StreamingExporter hashing + manifest writing + curator wiring + tests (DI-01, DI-02, DI-03)
- [x] 03-02-PLAN.md — manifest_verify() library function + tests + core exports (DI-04)

### Phase 4: CLI Jobs & Files Commands
**Goal**: Users can list available jobs from a config and inspect downloaded files with integrity verification
**Depends on**: Phase 3
**Requirements**: CLI-01, CLI-02, CLI-03
**Success Criteria** (what must be TRUE):
  1. `biocurator jobs` with no arguments auto-detects `biocurator_config.yaml` in CWD and lists all jobs; if the default file doesn't exist, shows a clear error directing the user to specify a config path
  2. `biocurator files my_job` lists downloaded files for a specific job with metadata from the manifest (path, format, size, checksum, record count)
  3. `biocurator files --verify` re-reads files from disk, recomputes checksums, compares against manifest, and reports any corruption clearly
  4. `biocurator files` without a job name shows all jobs that have downloaded files
  5. All command outputs use Rich tables for human-readable display with consistent formatting
**Plans**: 3 plans in 2 waves

**Wave 1 (independent — can run in parallel):**
- [x] 04-01-PLAN.md — `biocurator jobs` command + main.py registration + tests (CLI-01)
- [x] 04-02-PLAN.md — `biocurator files` list mode + main.py registration + tests (CLI-02)

**Wave 2 *(blocked on Wave 1 completion)*:**
- [x] 04-03-PLAN.md — `biocurator files --verify` mode + exit codes + tests (CLI-03)

**Cross-cutting constraints:**
- All commands default to `biocurator_config.yaml` (not `config.yaml`)
- All table output uses `header_style="bold magenta"` per status.py convention
- `manifest_verify()` from `biocurator.core` is the only verification backend

### Phase 5: Pre-flight Check & Integration
**Goal**: Users can optionally check server health before running a job; all reliability features work together coherently
**Depends on**: Phase 2, Phase 4
**Requirements**: STATUS-04, CFG-03
**Success Criteria** (what must be TRUE):
  1. `biocurator run my_job --check` probes provider health before executing the job and reports status
  2. If pre-flight check detects an unreachable provider, user sees a clear warning with option to proceed or abort
  3. Pre-flight check toggle can be set in job config YAML (`search.preflight_check: true/false`)
  4. Existing configs without `preflight_check` field parse without error (backward compatible)
  5. All reliability features (retry, circuit breaker, health checks, manifests, verify) work together without interference
**Plans**: 2 plans in 1 wave

Plans:
- [x] 05-01-PLAN.md — Config schema + parser for preflight_check (SearchConfig field, ConfigLoader parsing, tests)
- [x] 05-02-PLAN.md — Pre-flight health check in run command (--check/--no-check flags, health probes, Rich table, interactive prompt, tests)

### Phase 6: Retrospective Verification (Phase 01 & 04)
**Goal**: Create formal VERIFICATION.md documents for Phase 01 (Error Handling & Retry) and Phase 04 (CLI Jobs & Files) to confirm all built code satisfies original requirements
**Depends on**: Phase 1, Phase 4 (code already built)
**Requirements**: ERR-01, ERR-02, ERR-03, ERR-04, CFG-01, CLI-01, CLI-02, CLI-03
**Gap Closure**: Closes 8 unsatisfied requirements from audit (missing VERIFICATION.md)
**Success Criteria** (what must be TRUE):
  1. 01-VERIFICATION.md exists and confirms ERR-01..04 and CFG-01 are satisfied with code evidence
  2. 04-VERIFICATION.md exists and confirms CLI-01..03 are satisfied with code evidence

### Phase 7: Circuit Breaker Critical Fixes
**Goal**: Fix three blocking bugs found by the milestone audit — breaker_state returns object repr, main curator loses global_breaker, and status display is broken
**Depends on**: Phase 2 (code already built)
**Requirements**: CB-04, STATUS-03
**Gap Closure**: Closes 2 unsatisfied requirements + 1 HIGH-severity integration gap (BREAK-01)
**Success Criteria** (what must be TRUE):
  1. `breaker_state` property returns human-readable strings (`'closed'`/`'open'`/`'half_open'`) instead of Python object repr
  2. `run.py` main curator path passes `global_breaker=global_config.breaker` so circuit breakers are active when `--check` is not used
  3. `biocurator status` displays breaker state correctly using color-coded state names

### Phase 8: Circuit Breaker Tech Debt Cleanup
**Goal**: Fix remaining Phase 02 bugs (success_threshold, merge recreates breaker) and add test coverage; wire retry/breaker into preview curator
**Depends on**: Phase 7 (breaker fixes)
**Requirements**: CB-01, CB-03 (partial — fix gaps)
**Gap Closure**: Closes 3 Phase 02 tech debt items + 1 LOW-severity integration gap (BREAK-02)
**Success Criteria** (what must be TRUE):
  1. `success_threshold` parameter reaches pybreaker so half-open max successes is configurable
  2. `run_job()` merge properly recreates `_breaker` instances when config changes (per-db breakers work)
  3. Breaker-related code has test coverage (BreakerConfig, `_init_breaker()`, `breaker_state`, `HealthChecker`, `status_command`)
  4. Preview curator receives retry and breaker config so preview benefits from configured reliability

### Phase 9: Checksums Code Review Fixes
**Goal**: Fix 5 code review findings from Phase 03 checksums/manifests implementation
**Depends on**: Phase 3 (code already built)
**Requirements**: DI-01, DI-02, DI-03, DI-04 (hardening)
**Gap Closure**: Closes 5 code review findings (CR-01 through CR-05)
**Success Criteria** (what must be TRUE):
  1. `_hash_state` is reset in `StreamingExporter.open()` so reused exporter gets correct checksums (CR-01)
  2. `__exit__` does not write manifest after exceptions — truncated files aren't recorded (CR-02)
  3. `manifest_verify()` catches `json.JSONDecodeError` with a clear error message (CR-03)
  4. `verify_file` uses streaming/chunked reads instead of `read_bytes()` to avoid OOM on large files (CR-04)
  5. Incremental hasher and file verifier use consistent encoding (CR-05)

### Phase 10: Cleanup & Polish
**Goal**: Remove orphaned code and complete outstanding human UAT
**Depends on**: Phase 5 (pre-flight check code built)
**Requirements**: None (tech debt cleanup)
**Gap Closure**: Closes 2 optional technical debt items
**Success Criteria** (what must be TRUE):
  1. `utils/network.py` orphaned stub is deleted (13 lines, no imports, safe to remove)
  2. Phase 05 human UAT document is reviewed and completed (live API smoke test)

## Progress

**Execution Order:** Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Error Handling & Retry Foundation | 3/3 | Complete | 2026-05-25 |
| 2. Circuit Breaker & Health Status | 3/3 | Complete   | 2026-05-25 |
| 3. Checksums & Manifests | 2/2 | Complete   | 2026-05-25 |
| 4. CLI Jobs & Files Commands | 3/3 | Complete | 2026-05-26 |
| 5. Pre-flight Check & Integration | 2/2 | Complete   | 2026-05-25 |
| 6. Retrospective Verification | 0/0 | Planned | — |
| 7. Circuit Breaker Critical Fixes | 0/0 | Planned | — |
| 8. Circuit Breaker Tech Debt Cleanup | 0/0 | Planned | — |
| 9. Checksums Code Review Fixes | 0/0 | Planned | — |
| 10. Cleanup & Polish | 0/0 | Planned | — |
