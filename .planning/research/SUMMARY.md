# Project Research Summary

**Project:** Biocurator
**Domain:** Config-driven bioinformatics CLI tool for sequence curation from NCBI/UniProt
**Researched:** 2026-05-25
**Confidence:** HIGH (established patterns across all areas)

## Executive Summary

Biocurator is a config-driven CLI tool (v0.2.0) for curating biological sequence datasets from NCBI and UniProt. This milestone moves from a working-but-fragile tool to one with proper reliability patterns — configurable retry, circuit breakers, health checks, data integrity verification, and transparent error propagation. The research covers four areas: stack additions, feature landscape, architecture integration, and domain pitfalls.

**The recommended approach is additive and conservative.** The existing codebase has a solid layered architecture (CLI → Config → Core → Providers → Utils) with streaming generators. This milestone adds reliability layers without refactoring existing components: `tenacity` replaces the custom `@retry` decorator, a lightweight circuit breaker wraps provider methods, `hashlib` incremental hashing adds checksums during export, and a JSON manifest tracks job provenance. Three new CLI commands (`status`, `jobs`, `files`) provide user visibility into what the tool is doing.

**The single most critical risk is that silent error swallowing (`except Exception: return []`) in all searchers will undermine every reliability feature.** Circuit breakers never trigger because exceptions are caught internally. Retry configuration is invisible to the user. Checksum verification failures are logged as warnings that nobody sees. **Fixing error swallowing must be the absolute first task**, before any other reliability feature is implemented. The next most dangerous risk is the circuit breaker and retry layer fighting each other — they must be designed together, with the circuit breaker wrapping the retry decorator (not the reverse), and separate per-provider breakers.

## Key Findings

### Recommended Stack

The current stack (Typer 0.25.1, Rich 15.0.0, requests 2.34.2, biopython 1.87) remains unchanged. This milestone adds **two new production dependencies** and uses stdlib for the rest:

**Core technologies:**
- **`tenacity` >= 9.1**: Replace the custom 80-line `@retry` decorator with a battle-tested retry library supporting per-provider config (max_attempts, exponential backoff with jitter, `before_sleep_log` for observability, retry statistics for CLI status display) — 389M monthly downloads, actively maintained
- **`pybreaker` >= 1.4**: Per-provider circuit breaker with configurable failure threshold, reset timeout, and listener hooks for state change logging — 21M monthly downloads, built-in thread safety
- **`hashlib.file_digest()`** (Python 3.11+ stdlib): Efficient SHA-256 checksum computation during export, no dependencies beyond stdlib
- **`json` + `dataclasses`** (stdlib): Manifest file format — JSON is universally readable, simple to implement, and easy for users to inspect
- **`requests`** (already in stack): Health checker probes use lightweight HTTP GETs to `einfo` (NCBI) and the REST API root (UniProt) — no new HTTP library needed

**Notable rejections:** `backoff` (archived upstream), `httpx` (would require replacing all requests calls), `aiobreaker` (async-native for sync CLI), `cryptography` (stdlib hashlib suffices), `rest-health`/`pulsecheck-py` (designed for web frameworks, not CLI probing).

### Expected Features

**Must have (table stakes):**
- **Fix silent error swallowing** (TS-04) — the #1 reliability gap, prerequisite for everything else
- **`status` command** (TS-01) — probe NCBI/UniProt availability, report per-endpoint with response times
- **`jobs [config.yaml]` command** (TS-02) — list available jobs with descriptions from YAML config
- **`files [job_name]` command** (TS-03) — list downloaded files with metadata from per-job manifest
- **Per-provider configurable retry** (TS-05) — max_attempts, backoff_factor, timeout in DatabaseConfig
- **SHA-256 checksums on all downloads** (TS-07) — computed during export, stored in manifest
- **`files --verify`** (TS-08) — verify stored checksums against on-disk files to detect corruption
- **Error classification** (TS-09) — separate transient (network, 5xx) from permanent (4xx, parse) errors

**Should have (competitive/differentiators):**
- **Circuit breaker** (DF-01) — prevents cascading failures when a server is down; rare in bioinformatics CLI tools
- **Rich per-job manifest** (DF-03) — job name, provider, timestamps, record counts, source URLs, checksums
- **Graceful degradation summary** (DF-05) — end-of-job table showing successes vs failures with error breakdown
- **JSON output mode** (TS-10) — `--json` flag on status/jobs/files for script consumption
- **Pre-flight health check** (DF-02) — optional `--check-health` flag on `run` command

**Defer (future milestone):**
- Azure: `jobs --graph` (DF-06) — no DAG between jobs yet; no dependency visualization needed
- Auto-resume partial downloads — streaming model makes this impractical; re-run is simple
- Parallel/multi-threaded downloads — conflicts with NCBI Entrez usage guidelines
- Retry-After header support (TS-06) — valuable but P2; can be added later without breaking changes

### Architecture Approach

The architecture is additive — six new modules that compose with existing components without refactoring. Reliability is layered: circuit breaker wraps provider public methods (class-level state shared across instances, per-provider), retry wraps internal network calls (per-call). Checksums are computed incrementally in the StreamingExporter during write. Manifests are assembled at the CLI level after `run_job()` returns, not in the streaming pipeline.

**Major components:**
1. **`utils/circuit_breaker.py`** — Decorator-based circuit breaker per provider (class-level state dict), wraps provider search/fetch_metadata/download methods; failure counting is based on consecutive *unrecovered* failures after retry exhaustion
2. **`core/health.py`** — `HealthChecker` with per-provider probes (NCBI `einfo`, UniProt `/uniprotkb/search?query=*&size=1`), returns typed `HealthReport` with per-endpoint status + circuit state
3. **`core/exporter.py`** (modified) — Add incremental SHA-256 hashers and record counters per output format; checksums finalized on `close()`
4. **`core/manifest.py`** — `ManifestBuilder` that constructs and writes `JobManifest` JSON with file entries (path, format, size, sha256, records), job config snapshot, summary stats
5. **`cli/commands/status.py`, `jobs.py`, `files.py`** — Three new CLI commands using Rich tables for display
6. **`exceptions.py`** (modified) — Add `CircuitBreakerError`, `HealthCheckError`, `ManifestError`, `ChecksumMismatchError`

**Key patterns:** decorator-based cross-cutting concerns (circuit breaker mirrors existing `@retry` pattern), composition over inheritance (breaker wraps searcher, not subclass), backwards-compatible config evolution (all new `DatabaseConfig` fields have `None` defaults).

### Critical Pitfalls

1. **Circuit breaker fights the retry mechanism (C1):** Two resilience layers with overlapping error classification cause premature circuit openings. Retry handles transient failures; circuit breaker handles sustained outages. **Mitigation:** One breaker per provider (never shared), circuit breaker wraps the retry decorator (sees one "failure" per batch after retries exhaust, not every raw failure), rate-limit errors (429) excluded from breaker counts, failure threshold set generously (10-20 consecutive failures).

2. **Retry on all exceptions including non-recoverable (C2):** Current `@retry` catches all `Exception` — it retries `AttributeError` (coding bugs), `ValueError` from `Entrez.read()` (parse errors), and `MemoryError`. **Mitigation:** Change default to catch only `requests.RequestException`, `urllib3.exceptions.HTTPError`, and `IOError`. Separate network fetch (retryable) from XML parsing (not retryable) into distinct try/except blocks. Add explicit non-retryable exception list.

3. **Checksum done wrong — false confidence (C3):** Streaming checksums computed from write buffer (not on-disk file) catch nothing if the write corrupted. Storing checksums alongside the data in the output directory means both get corrupted together. **Mitigation:** Always verify by re-reading the completed on-disk file. Store a manifest checksum chain-of-trust (BagIt-style). `--verify` must recompute and compare, not just check manifest existence.

4. **Status command false positives/negatives (C4):** Probing `www.ncbi.nlm.nih.gov` (CDN) while the actual `eutils` API is down gives false positive. A rate-limited probe (429) is reported as "unavailable" — false negative. **Mitigation:** Probe the actual API endpoints (`einfo` for NCBI, `rest.uniprot.org` for UniProt). Report per-endpoint status (search vs fetch independently). Distinguish "unreachable" from "rate-limited" in status messages. Include response time. Cache results for 30-60s.

5. **Silent error swallowing undermines all reliability improvements (C10):** `except Exception: logger.warning(...); return []` in every searcher method catches circuit breaker exceptions, retry exhaustion, and checksum failures. All reliability features become invisible. **Mitigation:** Remove ALL `except Exception: return []` blocks before adding any new reliability feature. This is the prerequisite — the first task, not the fifth.

6. **Manifest format becomes unmaintainable (C5):** Custom JSON formats lock users into the tool; schema evolves without versioning; no standard tooling can verify. **Mitigation:** Follow BagIt-style `manifest-sha256.txt` format (verifiable with standard `sha256sum -c`). Use relative paths. Record algorithm in filename. Document format.

## Implications for Roadmap

### Phase 1: Error Propagation Fix + Retry Upgrade (Foundation)
**Rationale:** Everything depends on this. Silent error swallowing makes all other reliability features invisible. The retry upgrade is the natural integration point for per-provider configuration.
**Delivers:** Error propagation through the exception hierarchy, tenacity replacing custom `@retry`, per-provider retry config in `DatabaseConfig`
**Addresses:** TS-04 (fix silent swallowing), TS-05 (per-provider retry config), part of TS-09 (error classification — separate transient from permanent at the retry boundary)
**Stack additions:** `tenacity >= 9.1`
**Avoids:** C2 (retry on all exceptions — implement narrow exception targeting), C10 (silent swallowing — remove all `except Exception: return []` blocks first)
**Pitfall C11:** All new numeric config fields use `is not None`, never truthiness checks. Add explicit test for value=0.

### Phase 2: Circuit Breaker + Health Checks (Reliability Layer)
**Rationale:** Circuit breaker requires Phase 1's error propagation (if exceptions don't propagate, the breaker never triggers). Health checks compose naturally with circuit state. Building these together ensures the breaker→retry composition is correct.
**Delivers:** `utils/circuit_breaker.py`, `core/health.py`, `cli/commands/status.py`, exception types, status command
**Addresses:** TS-01 (status command), DF-01 (circuit breaker), part of RELIAB-03, RELIAB-04, CLI-01
**Stack additions:** `pybreaker >= 1.4`
**Avoids:** C1 (separate breaker per provider, breaker wraps retry not vice versa), C4 (probe real API endpoints, per-endpoint status, distinguish rate-limited from unreachable)
**⚠ RESEARCH FLAG:** There is a discrepancy between research sources on circuit breaker implementation. STACK.md recommends `pybreaker` library; ARCHITECTURE.md designs a fully custom `CircuitBreaker` class. The custom approach is simpler (~150 LOC) and avoids adding a dependency for a 3-state machine. ARCHITECTURE.md's approach is preferred for a local CLI tool (avoids over-engineering per PITFALL C6). **Decision to make during Phase 2 planning: use pybreaker or custom implementation.**

### Phase 3: Checksums + Manifest System (Data Integrity)
**Rationale:** Checksum computation in the exporter is self-contained (no dependencies on other phases beyond the exception types from Phase 1). The manifest system builds on checksums. Both can be developed in parallel with Phase 2.
**Delivers:** Incremental SHA-256 hashing in `StreamingExporter`, `core/manifest.py`, file manifest JSON
**Addresses:** TS-07 (SHA-256 checksums), DI-01/DI-02 (checksum generation, per-job manifest)
**Stack additions:** `hashlib` (already stdlib), `json` (already stdlib)
**Avoids:** C3 (verify from disk, not buffer — architecture's incremental hashing approach conflicts with this; **reconciliation needed — see below**), C5 (manifest format — use BagIt-style `manifest-sha256.txt` for compatibility with standard `sha256sum -c`)
**⚠ RESEARCH FLAG:** Critical tension. FEATURES.md and ARCHITECTURE.md recommend computing SHA-256 incrementally during streaming write (efficient, zero extra passes). PITFALL C3 explicitly warns this gives "false confidence" — buffer-to-disk write corruption is not detected. **Reconciliation decision needed:** Option A (preferred) — compute checksums during streaming for speed AND verify from disk on `--verify` command. The streaming checksum serves as a quick check; the disk re-read catches buffer write corruption. Option B (recommended for integrity) — compute strictly from disk, adding an extra read pass. Decision impacts exporter complexity and performance.

### Phase 4: CLI Jobs + Files Commands (User Visibility)
**Rationale:** These commands depend on manifest (Phase 3) for data. `jobs` reads config (already exists), `files` reads manifest. `files --verify` adds verification.
**Delivers:** `cli/commands/jobs.py`, `cli/commands/files.py`, `files --verify` command, `--json` output mode
**Addresses:** TS-02 (jobs command), TS-03 (files command), TS-08 (files --verify), CLI-02, CLI-03, TS-10 (--json mode)
**Avoids:** C4 (status nuance — per-endpoint, with degradation states)
**Parallelizable:** `jobs` (reads config only) and `files` (reads manifest) are independent once manifest schema is designed. Can be built in parallel.

### Phase 5: Integration + Polish (Completion)
**Rationale:** Tie everything together. Pre-flight health check on `run`, graceful degradation summary, config schema enrichment, manifest enrichment.
**Delivers:** `--check-health` flag on `run` command, end-of-job error summary table, rich manifest with provider health snapshot, YAML reliability config section
**Addresses:** DF-02 (pre-flight check), DF-03 (rich manifest), DF-05 (degradation summary)
**Avoids:** C7 (backwards-compatible config — all new YAML fields optional with `None` defaults, test old configs in CI)

### Phase Ordering Rationale

- **Phase 1 must be first** because error propagation is the foundation. Every other reliability feature depends on exceptions being visible. Without this, circuit breakers don't trigger, checksum mismatches go unreported, and retry configuration is invisible.
- **Phases 2 and 3 can be parallelized** — they share no module dependencies. Circuit breaker (Phase 2) and checksums/manifest (Phase 3) touch completely different parts of the codebase.
- **Phase 4 depends on Phase 3** (manifest), but `jobs` command within Phase 4 depends only on config loading (existing) — it can start early.
- **Phase 5** is the integration layer that makes everything work together — pre-flight checks, degradation summaries, and config enrichment.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1:** NCBI API compatibility auditing. Pitfalls C8 documents several edge cases (WebEnv expiration, retmax hard cap, XML schema changes, Bio.Entrez internal rate limiting interaction). A dedicated audit of the `NCBISearcher` implementation against these known gotchas would prevent post-release bugs.
- **Phase 2:** Circuit breaker implementation decision. The pybreaker vs custom-implementation question needs a concrete decision. A brief spike (1-2 hours) comparing the two approaches would resolve this.
- **Phase 3:** Checksum strategy finalization. The streaming-vs-disk-vs-both checksum question needs a technical decision based on threat model. For a local CLI tool on a workstation, disk-write corruption is extremely rare (ZFS/Btrfs/ext4 checksum data). Streaming checksum is likely sufficient, with `--verify` providing the disk re-read path on demand.

Phases with standard patterns (skip research-phase):
- **Phase 4:** CLI commands. Adding Typer commands to an existing app is well-documented. The pattern is established by `init.py`, `run.py`, and `preview.py`. No additional research needed.
- **Phase 5:** Integration. Wiring existing components together follows standard patterns. No niche domain knowledge needed.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | No version ambiguity. `tenacity` and `pybreaker` are well-established, PyPI-monthly-download-verified. stdlib usage (`hashlib`, `json`) requires no confidence assessment. |
| Features | HIGH | Feature landscape derived from direct comparison with 7 similar tools (EDirect, sra-tools, NCBI Datasets CLI, genomebundle, etlplus, feather ETL, oxo-flow). Table stakes vs differentiators clearly defined. Feature dependency graph validates priorities. |
| Architecture | HIGH | Based on existing codebase analysis (.planning/codebase/ARCHITECTURE.md, STRUCTURE.md, CONCERNS.md) + established patterns (circuit breaker from Nygard *Release It!*, streaming hashing from Python stdlib docs, Typer command docs). No speculative architecture. |
| Pitfalls | HIGH | 11 critical pitfalls with concrete prevention strategies. Each rooted in either existing codebase analysis (CONCERNS.md), documented API behavior (NCBI E-utilities docs, BagIt RFC), or known anti-patterns (over-mocking, over-engineering). |

**Overall confidence:** HIGH

### Gaps to Address

1. **Checksum strategy tension:** FEATURES.md/ARCHITECTURE.md propose streaming incremental checksums; PITFALLS C3 warns this gives false confidence. **Resolution:** Use streaming checksums for efficiency (catches download corruption), mandate disk-based verification on `--verify` path. Document the trade-off.
2. **Circuit breaker implementation choice:** STACK.md recommends `pybreaker`; ARCHITECTURE.md designs a custom class. **Resolution:** Make a pragmatic decision during Phase 2 planning. For a local CLI tool, a custom ~150-line implementation is likely simpler and avoids a dependency. If thread safety or more complex state management is needed, use pybreaker.
3. **Manifest storage location:** ARCHITECTURE.md stores manifest in output directory (`results/.biocurator_manifest.json`); PITFALLS C3 recommends outside the output directory for split-brain protection. **Resolution:** Use the BagIt `manifest-sha256.txt` approach — store the primary manifest in the output directory (where users expect it) and optionally write a lightweight tag manifest to `~/.local/share/biocurator/manifests/` for truly paranoid verification. For v0.3.0, the output directory manifest is sufficient.
4. **`Entrez.tool` not set:** Minor PITFALL m2 — the code sets `Entrez.email` but not `Entrez.tool`. NCBI can't distinguish biocurator traffic from generic Biopython. **Resolution:** Fix in Phase 1 alongside error propagation changes. Set `Entrez.tool = "biocurator/v0.3.0"`.
5. **Rate limit interaction with Bio.Entrez:** Biopython's internal rate limiting (`Bio.Entrez.sleep_before_try`) interacts unpredictably with the tool's own `rate_limit` config. **Resolution:** Audit during Phase 1. Document the combined behavior. Consider disabling Bio.Entrez's internal throttle and relying entirely on the tool's own configurable rate limiting.

## Sources

### Primary (HIGH confidence)
- **Current codebase analysis**: `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/STRUCTURE.md`, `.planning/codebase/CONCERNS.md` — verified existing architecture, patterns, and known issues
- **Project requirements**: `.planning/PROJECT.md` — validated active requirements (RELIAB-01 through RELIAB-04, CLI-01 through CLI-03, TEST-01 through TEST-03)
- **STACK.md research**: tenacity PyPI page, pybreaker PyPI page, Python `hashlib` docs — 389M/21M monthly downloads, actively maintained
- **NCBI E-utilities Documentation**: https://www.ncbi.nlm.nih.gov/books/NBK25501/ — usage guidelines, WebEnv, rate limits
- **BagIt RFC 8493**: https://www.rfc-editor.org/rfc/rfc8493 — standard manifest format for digital preservation
- **Michael T. Nygard, Release It!** — circuit breaker pattern reference

### Secondary (MEDIUM confidence)
- **FEATURES.md research**: Direct comparison with 7 similar tools (EDirect, sra-tools, NCBI Datasets CLI, genomebundle, etlplus, feather ETL, oxo-flow, QuickETL) — feature gaps and differentiators
- **PITFALLS.md research**: Self-healing data pipeline patterns, circuit breaker + retry interaction guidance (AWS, Microsoft Azure patterns), pytest CLI testing best practices
- **Biopython Entrez Tutorial**: https://biopython.org/docs/dev/Tutorial/chapter_entrez.html — rate limiting, API key support
- **Network reliability patterns**: https://learn.microsoft.com/en-us/azure/architecture/patterns/circuit-breaker — circuit breaker + retry interaction

### Tertiary (LOW confidence — single source)
- **genomebundle tool**: Single source for manifest/verify pattern — SHA256 checksums in `manifest.json`, `verify` command — referenced but not independently verified
- **oxo-flow tool**: Single source for CLI command patterns — `status`, `validate`, `lint`, `graph` — patterns validated by 6 other tools

---

*Research completed: 2026-05-25*
*Ready for roadmap: yes*
