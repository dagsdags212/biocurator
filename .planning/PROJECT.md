# Biocurator

## What This Is

A config-driven command-line tool for curating biological sequence datasets from NCBI and UniProt. Users define curation jobs in YAML (search criteria, filters, export formats) and run them via CLI to reliably download and verify FASTA, CSV, or JSON data.

## Core Value

Reliably download verified biological sequence data from public databases with a single CLI command, even across intermittent network failures.

## Requirements

### Validated

- ✓ Config-driven pipeline: YAML defines multi-job workflows with search, filter, export phases — existing
- ✓ NCBI Entrez provider: search (`esearch` with history), metadata fetch (`esummary`), sequence download (`efetch`) — existing
- ✓ UniProt REST API provider: search (`/uniprotkb/search`), metadata fetch, FASTA download — existing
- ✓ Streaming export: FASTA, CSV, JSON formats via `StreamingExporter` with memory-efficient iterators — existing
- ✓ CLI with Typer + Rich: `init`, `run`, `preview` commands with progress bars and tables — existing
- ✓ Config validation at load time: typed dataclass schema with required field checks — existing
- ✓ Exponential backoff retry: decorator-based `@retry` on all network calls — existing
- ✓ Sequence filtering: length, organism, exclude terms, quality threshold — existing
- ✓ Typed exception hierarchy: `BiocuratorError` with 7 subtypes — existing
- ✓ Rate limiting: configurable per-provider delay between requests — existing
- ✓ Provider registry: plugin-style `ProviderRegistry` for discovering searchers — existing
- ✓ CI via GitHub Actions: tests on push/PR, publish on release — existing
- ✓ Retry via tenacity: per-provider `RetryConfig` with max_attempts, backoff_factor, max_delay, timeout — Phase 1
- ✓ Narrow exception targeting: network errors retried, data/parse errors not — Phase 1
- ✓ Circuit breaker: per-provider pybreaker wrapping searcher public methods — Phase 2
- ✓ BreakerConfig: fail_max, recovery_timeout, half_open_max_successes in DatabaseConfig — Phase 2
- ✓ HealthChecker: NCBI Entrez and UniProt REST API availability probes — Phase 2
- ✓ `biocurator status` CLI: Rich table with Provider, Status, Response Time, Breaker State — Phase 2
- ✓ Pre-flight check config toggle: `search.preflight_check: true/false` in YAML (CFG-03) — Phase 5
- ✓ Pre-flight health check CLI: `biocurator run --check`/`--no-check` probes providers before job execution (STATUS-04) — Phase 5
- ✓ Circuit breaker global wiring: `global_breaker` correctly passed to main curator path (BREAK-01 fix) — Phase 7
- ✓ `breaker_state` returns human-readable `'closed'/'open'/'half_open'` strings (CB-04) — Phase 7
- ✓ `biocurator status` displays color-coded breaker state names (STATUS-03) — Phase 7

### Active

#### Reliability

- ✓ **RELIAB-01**: Fixed silent error swallowing in `NCBISearcher` and `UniProtSearcher` — exceptions propagate via `DatabaseSearchError` — Phase 1
- ✓ **RELIAB-02**: Granular, configurable retry settings per provider (max_attempts, backoff_factor, max_delay, timeout) in `DatabaseConfig` — Phase 1
- ✓ **RELIAB-03**: Circuit breaker pattern to prevent cascading failures when a server is down — Phase 2
- ✓ **RELIAB-04**: Server health check endpoint via `biocurator status` CLI — Phase 2

#### CLI Commands

- ✓ **CLI-01**: `biocurator status` — probe NCBI/UniProt API availability and report status — Phase 2
- [ ] **CLI-02**: `biocurator jobs [config.yaml]` — list available jobs from a config file with descriptions
- [ ] **CLI-03**: `biocurator files [job_name]` — list downloaded files with per-job manifest metadata

#### Data Integrity

- [ ] **TEST-01**: Generate checksums (SHA-256) for all downloaded sequence files during export
- [ ] **TEST-02**: Store checksums in per-job manifest files alongside download metadata
- [ ] **TEST-03**: `biocurator files --verify` — verify stored checksums to detect data corruption

### Out of Scope

- GUI or web interface — CLI-only tool
- Adding new database providers beyond NCBI and UniProt
- Automated CI integration tests hitting real external APIs (test with fixtures/mocks only)
- Containerization (Docker) — local CLI tool only
- Multi-user or server deployment — single-user workstation tool

## Context

Existing codebase at v0.2.0 with ~5,000 files. Key architectural traits:

- **Layered architecture**: CLI → Config → Core → Providers → Utils
- **Streaming pipeline**: generators (`Iterator[SequenceRecord]`) for memory-efficient dataset processing
- **Provider abstraction**: `DatabaseSearcher[C]` ABC with `NCBISearcher` and `UniProtSearcher` implementations
- **Known concerns**: Silent error swallowing in searchers (HIGH), duplicate logic between `run_job` and `preview_command` (MEDIUM), lazy `_json_count` init pattern (MEDIUM), limited test coverage (127 tests across 10 files)
- **Current CLI commands**: `init`, `run CONFIG`, `preview JOB_NAME`

## Constraints

- **Python**: Must support Python 3.13+ (enforced in pyproject.toml)
- **API compliance**: Must respect NCBI Entrez usage guidelines (rate limits, email identification)
- **Backwards compatibility**: Existing YAML config format must remain valid
- **No external services**: All functionality must work offline except the database API calls themselves

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Checksum on download + verify on re-run | Catches both download corruption and storage bit-rot | Validated in Phase 3 — SHA-256 computed incrementally during streaming export |
| Per-job manifest files | Associates checksums with specific curation runs for traceability | Validated in Phase 3 — manifest.json + manifest-sha256.txt written by StreamingExporter |
| Circuit breaker over infinite retry | Prevents hammering a downed server and gives fast feedback | Validated in Phase 2 — per-provider pybreaker; Phase 7 — BREAK-01 global_breaker wiring fix |
| Server status as CLI command + pre-flight check | Lets users probe before running and optionally auto-check | Validated in Phase 2 — `biocurator status` CLI; Phase 5 — pre-flight `--check` integration |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-26 after Phase 7 execution*
