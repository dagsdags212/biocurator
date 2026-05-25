# Requirements: Biocurator

**Defined:** 2026-05-25
**Core Value:** Reliably download verified biological sequence data from public databases with a single CLI command, even across intermittent network failures.

## v1 Requirements

### Error Handling & Retry

- [ ] **ERR-01**: Fix silent error swallowing in `NCBISearcher` and `UniProtSearcher` — exceptions should propagate or be surfaced clearly, never `return []`
- [ ] **ERR-02**: Narrow caught exceptions in searchers from `Exception` to `requests.RequestException` (and domain-specific types)
- [ ] **ERR-03**: Replace custom `@retry` decorator with `tenacity` for configurable, per-provider retry strategies
- [ ] **ERR-04**: Add retry configuration to `DatabaseConfig` — `max_attempts`, `backoff_factor`, `max_delay`, `timeout`

### Circuit Breaker

- [ ] **CB-01**: Add per-provider circuit breaker that prevents cascading failures when a server is down
- [ ] **CB-02**: Integrate circuit breaker with existing provider layer — wrap searcher public methods
- [ ] **CB-03**: Add circuit breaker configuration to `DatabaseConfig` — failure threshold, recovery timeout, half-open max retries
- [ ] **CB-04**: Expose circuit breaker state for observability (CLI status command and logs)

### Health Checks & CLI Status

- [ ] **STATUS-01**: Build `HealthChecker` that probes NCBI Entrez and UniProt REST API availability
- [ ] **STATUS-02**: `biocurator status` command — probe all configured providers and report health per-provider
- [ ] **STATUS-03**: Show circuit breaker state in status output (open/closed/half-open counts)
- [ ] **STATUS-04**: Optionally run health check as pre-flight before job execution (`biocurator run --check`)

### CLI Jobs & Files

- [ ] **CLI-01**: `biocurator jobs [CONFIG]` — list available jobs from a config file with descriptions and database targets
- [ ] **CLI-02**: `biocurator files [JOB_NAME]` — list downloaded files, with optional per-job filtering
- [ ] **CLI-03**: `biocurator files --verify` — verify stored checksums to detect data corruption or bit-rot

### Data Integrity

- [ ] **DI-01**: Generate SHA-256 checksums for all downloaded sequence files during streaming export
- [ ] **DI-02**: Store checksums in per-job manifest files (JSON, BagIt-compatible format) alongside download metadata
- [ ] **DI-03**: Manifest includes job config snapshot, timestamps, record counts, provider info for provenance
- [ ] **DI-04**: `--verify` flag re-reads files from disk and compares checksums against manifest

### Configuration

- [ ] **CFG-01**: Add retry, circuit breaker, and timeout fields to `DatabaseConfig` schema — all optional with sensible defaults
- [ ] **CFG-02**: Ensure backward compatibility — existing YAML configs without new fields must parse without error
- [ ] **CFG-03**: Add pre-flight check toggle to job config (`search.preflight_check: true/false`)

## v2 Requirements

### Advanced Reliability

- **V2-01**: Persistent circuit breaker state across process restarts (cache to `~/.cache/biocurator/`)
- **V2-02**: Degradation summaries in job output — how many retries, which providers had issues
- **V2-03**: `biocurator status --watch` for continuous monitoring with configurable interval

### CLI Polish

- **V2-04**: `--json` output flag on all commands for machine-parseable output
- **V2-05**: Tab completion for job names and config file paths
- **V2-06**: Export manifest in BagIt format for interoperability with archival tools

## Out of Scope

| Feature | Reason |
|---------|--------|
| Web GUI or dashboard | CLI-only tool, scope creep |
| New database providers (beyond NCBI/UniProt) | Not requested, increases scope significantly |
| Docker/containerization | Single-user CLI tool, adds maintenance burden |
| Real API calls in CI tests | Unreliable, rate-limited, violates API terms |
| Async I/O or asyncio refactor | Requires significant rewrite, not justified for CLI tool |
| Metrics/telemetry export | Over-engineering for a local CLI tool |
| Database-backed manifest storage | JSON files are simpler and sufficient for single-user |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| ERR-01 | | Pending |
| ERR-02 | | Pending |
| ERR-03 | | Pending |
| ERR-04 | | Pending |
| CB-01 | | Pending |
| CB-02 | | Pending |
| CB-03 | | Pending |
| CB-04 | | Pending |
| STATUS-01 | | Pending |
| STATUS-02 | | Pending |
| STATUS-03 | | Pending |
| STATUS-04 | | Pending |
| CLI-01 | | Pending |
| CLI-02 | | Pending |
| CLI-03 | | Pending |
| DI-01 | | Pending |
| DI-02 | | Pending |
| DI-03 | | Pending |
| DI-04 | | Pending |
| CFG-01 | | Pending |
| CFG-02 | | Pending |
| CFG-03 | | Pending |

**Coverage:**
- v1 requirements: 22 total
- Mapped to phases: 0
- Unmapped: 22 ⚠️

---
*Requirements defined: 2026-05-25*
*Last updated: 2026-05-25 after initial definition*
