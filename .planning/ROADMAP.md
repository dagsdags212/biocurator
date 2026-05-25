# Roadmap: Biocurator

## Overview

Take a working-but-fragile bioinformatics CLI tool (silent error swallowing, custom retry, no data integrity) and harden it with proper reliability patterns — configurable retry via tenacity, per-provider circuit breakers, health checks, SHA-256 checksums, job manifests, and CLI commands for visibility. Each phase delivers a user-observable capability from the fix of silent failures through pre-flight health checks.

## Phases

- [ ] **Phase 1: Error Handling & Retry Foundation** - Fix silent error swallowing, migrate to tenacity retry, add per-provider retry config to schema
- [ ] **Phase 2: Circuit Breaker & Health Status** - Per-provider circuit breakers, `biocurator status` command with health probes and breaker state
- [ ] **Phase 3: Checksums & Manifests** - SHA-256 checksums during streaming export, per-job manifest files with provenance metadata
- [ ] **Phase 4: CLI Jobs & Files Commands** - `biocurator jobs`, `biocurator files`, and `files --verify` for data integrity verification
- [ ] **Phase 5: Pre-flight Check & Integration** - `biocurator run --check`, config pre-flight toggle, end-to-end reliability integration

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
**Plans**: TBD

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
**Plans**: TBD

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
**Plans**: TBD

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
**Plans**: TBD

## Progress

**Execution Order:** Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Error Handling & Retry Foundation | 0/3 | Planned | - |
| 2. Circuit Breaker & Health Status | 0/0 | Not started | - |
| 3. Checksums & Manifests | 0/0 | Not started | - |
| 4. CLI Jobs & Files Commands | 0/0 | Not started | - |
| 5. Pre-flight Check & Integration | 0/0 | Not started | - |
