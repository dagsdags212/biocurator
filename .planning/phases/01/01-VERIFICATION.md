---
phase: "01"
status: passed
verified: 2026-05-25T19:44:00Z
must_haves_verified: 5
must_haves_total: 5
requirements_covered: [ERR-01, ERR-02, ERR-03, ERR-04, CFG-01]
gaps: []
human_verification: []
---

# Phase 01: Error Handling & Retry Foundation — Verification Report

**Phase Goal:** Exceptions propagate clearly instead of silent empty results; retry uses tenacity with configurable per-provider settings; config schema accepts all new fields.

**Status:** ✅ PASSED — all 5 must-haves verified against the live codebase.

**Prior UAT:** 4/5 manual tests passed, 1 skipped (retry with live servers — hard to trigger, covered by unit tests). See `01-UAT.md`.

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `search()` raises `DatabaseSearchError` on failure; never silently returns `[]` | ✓ VERIFIED | NCBI `search()` line 112: `raise DatabaseSearchError(f"NCBI search error: {exc}")`. UniProt `search()` line 97: `raise DatabaseSearchError(f"UniProt search error: {exc}")`. All 6 public methods (search, fetch_metadata, download × 2 providers) wrap `Exception` in `DatabaseSearchError`. |
| 2 | Generators (fetch_metadata, download) catch-and-continue per-record with warnings | ✓ VERIFIED | NCBI `_do_fetch_metadata()` line 155: `logger.warning(...)` inside `except Exception` + continue. NCBI `_do_download()` line 214: `logger.warning(...)` per-record failure. UniProt `_do_fetch_metadata()` line 138: `logger.warning(...)` in batch loop. UniProt `_do_download()` line 178: `logger.warning(...)` per-accession failure. |
| 3 | Retry uses tenacity with configurable per-provider settings; custom `@retry` removed | ✓ VERIFIED | tenacity imported at `ncbi/searcher.py:9-14` and `uniprot/searcher.py:11-16` (`Retrying`, `before_sleep_log`, `stop_after_attempt`, `wait_exponential`). 3 call sites: `_safe_entrez_call()` (ncbi:68), `_fetch_single()` (ncbi:77), `_safe_get()` (uniprot:66). `utils/network.py:12-13`: comment states "Custom @retry removed in Phase 1". `pyproject.toml:38`: `tenacity>=9.1,<10.0`. |
| 4 | Retry only network-level exceptions; 4xx/parse errors never retried | ✓ VERIFIED | `retryable_exceptions.py:31`: `RETRYABLE_PREDICATE = retry_if_exception(_is_retryable)`. `_is_retryable()` at line 8-28 distinguishes 5xx (retryable, lines 16-18) from 4xx (not retryable). Retryable types: `requests.ConnectionError`, `requests.Timeout`, `urllib.error.URLError`, `socket.timeout`, `socket.gaierror` (lines 20-27). Non-retryable `ValueError`, `KeyError`, `TypeError` excluded via `_init_breaker()` at `base.py:142-146`. Entrez.read() parse outside retry block (ncbi:68-71). |
| 5 | Existing configs without retry/breaker fields parse without error (backward compatible) | ✓ VERIFIED | All `RetryConfig` fields are `Optional` with `None` default (`schema.py:6-9`). `ConfigLoader._parse()` line 40: `RetryConfig.from_dict(raw_retry) if raw_retry else None` — conditional, `None` if missing. `SearchConfig.retry: dict[str, RetryConfig] | None = None` at `schema.py:122`. Searchers fall back: `RetryConfig.defaults()` if `self.config.retry is None` (ncbi:48, uniprot:44-46). |

**Score:** 5/5 truths verified

---

## Requirements Coverage

### ✅ ERR-01 — Silent error swallowing fixed

**Evidence:**
- `src/biocurator/providers/ncbi/searcher.py` line 112: `search()` raises `DatabaseSearchError(f"NCBI search error: {exc}")` from caught `Exception`
- `src/biocurator/providers/ncbi/searcher.py` line 169: `fetch_metadata()` raises `DatabaseSearchError(f"NCBI metadata fetch failed: {exc}")`
- `src/biocurator/providers/ncbi/searcher.py` line 226: `download()` raises `DatabaseSearchError(f"NCBI download failed: {exc}")`
- `src/biocurator/providers/uniprot/searcher.py` line 97: `search()` raises `DatabaseSearchError(f"UniProt search error: {exc}")`
- `src/biocurator/providers/uniprot/searcher.py` line 152: `fetch_metadata()` raises `DatabaseSearchError(f"UniProt metadata fetch failed: {exc}")`
- `src/biocurator/providers/uniprot/searcher.py` line 193: `download()` raises `DatabaseSearchError(f"UniProt download failed: {exc}")`
- Both searchers re-raise `DatabaseSearchError` (don't double-wrap): `except DatabaseSearchError: raise` (ncbi:109, 166, 223; uniprot:94, 149, 190)
- Generators (internal `_do_*` methods) use `logger.warning()` + continue on per-record errors — never silently skip:
  - NCBI `_do_fetch_metadata()` line 155: `logger.warning(f"Error fetching metadata for batch ...")`
  - NCBI `_do_download()` line 214: `logger.warning(f"Failed to download sequence at index {i}: {exc}")`
  - UniProt `_do_fetch_metadata()` line 138: `logger.warning(f"Error fetching UniProt metadata for batch ...")`
  - UniProt `_do_download()` line 178: `logger.warning(f"Failed to download {uid}: {exc}")`
- `src/biocurator/exceptions.py` line 22: `DatabaseSearchError(BiocuratorError)` typed exception exists
- **Tests:** `tests/providers/ncbi/test_searcher.py` — `test_search_raises_database_search_error_on_network_failure` (line 95), `test_search_raises_database_search_error_on_retry_exhaustion` (line 106), `test_fetch_metadata_continues_on_batch_failure` (line 117), `test_download_continues_on_single_failure` (line 126)
- **Tests:** `tests/providers/uniprot/test_searcher.py` — `test_search_raises_database_search_error_on_failure` (line 58), `test_search_raises_database_search_error_on_http_400` (line 72), `test_fetch_metadata_continues_on_batch_failure` (line 91), `test_download_continues_on_single_failure` (line 103)

---

### ✅ ERR-02 — Narrowed caught exceptions

**Evidence:**
- `src/biocurator/utils/retryable_exceptions.py` line 31: `RETRYABLE_PREDICATE = retry_if_exception(_is_retryable)` — tenacity predicate driven by custom `_is_retryable()`
- `_is_retryable()` at line 8-28 implements the CONTEXT.md decision:
  - 5xx HTTP errors retryable (line 17): `exc.response.status_code >= 500` (requests) and line 18: `exc.code >= 500` (urllib)
  - 4xx HTTP errors NOT retryable — filtered by `_is_retryable()` returning `False` for `status_code < 500`
  - Retryable types (lines 19-27): `requests.ConnectionError`, `requests.Timeout`, `urllib.error.URLError`, `socket.timeout`, `socket.gaierror`
- Non-retryable types excluded from breaker via `_init_breaker()` at `src/biocurator/providers/base.py` lines 142-146: `exclude=[ValueError, KeyError, TypeError]`
- NCBI `_make_retryer()` line 56: `retry=RETRYABLE_PREDICATE` — wired into Retrying call
- UniProt `_make_retryer()` line 53: `retry=RETRYABLE_PREDICATE` — same wiring
- **Imports verified:** `ncbi/searcher.py:28` and `uniprot/searcher.py:25` both import `RETRYABLE_PREDICATE`
- **Detail:** `_safe_get()` in UniProt intentionally keeps `raise_for_status()` inside the `Retrying` block (line 66-67), so 5xx responses trigger retry and 4xx responses are filtered by `RETRYABLE_PREDICATE` — exactly as CONTEXT.md specifies
- **Tests:** `tests/utils/test_network.py` — 11 tests covering retryable exception classification

---

### ✅ ERR-03 — Custom @retry replaced with tenacity

**Evidence:**
- `pyproject.toml` line 38: `"tenacity>=9.1,<10.0"` dependency added
- `src/biocurator/providers/ncbi/searcher.py` lines 9-14: `from tenacity import Retrying, before_sleep_log, stop_after_attempt, wait_exponential`
- `src/biocurator/providers/uniprot/searcher.py` lines 11-16: same tenacity imports
- **3 call sites verified:**
  1. NCBI `_safe_entrez_call()` (line 67-71): `retryer = self._make_retryer()` → `handle = retryer(func, **kwargs)` then `Entrez.read(handle)` OUTSIDE retry block
  2. NCBI `_fetch_single()` (line 76-80): `retryer = self._make_retryer()` → `handle = retryer(Entrez.efetch, **params)` then `SeqIO.read(handle, "fasta")` OUTSIDE retry block
  3. UniProt `_safe_get()` (line 65-67): `retryer = self._make_retryer()` → `response = retryer(self.session.get, url, **kwargs)` → `response.raise_for_status()` INSIDE retry block (5xx retried, 4xx filtered by predicate)
- `before_sleep_log` provides retry attempt number and timing in logs per CONTEXT.md decision (ncbi:58, uniprot:55)
- `utils/network.py` line 12-13: `# NOTE: Custom @retry removed in Phase 1. # See utils/retryable_exceptions.py ...` — no `def retry` or `@retry` remaining
- No broken imports from custom `@retry` removal
- Retry config resolution uses `self.config.retry.resolve()` or `RetryConfig.defaults()` fallback (ncbi:48, uniprot:44-46)

---

### ✅ ERR-04 — RetryConfig in DatabaseConfig

**Evidence:**
- `src/biocurator/config/schema.py` lines 5-52: `RetryConfig` dataclass with fields:
  - `max_attempts: int | None = None` (line 6) — default 3 from `resolve()`
  - `backoff_factor: float | None = None` (line 7) — default 2.0 from `resolve()`
  - `max_delay: int | None = None` (line 8) — default 60 from `resolve()`
  - `timeout: int | None = None` (line 9) — default 30 from `resolve()`
- `resolve()` method (lines 11-37): cascading resolution — per-db > defaults param > hardcoded defaults (3, 2.0, 60, 30)
- `defaults()` classmethod (lines 39-41): `return cls().resolve()` — returns fully populated instance with all hardcoded defaults
- `from_dict()` classmethod (lines 44-52): parses YAML dict into `RetryConfig`, returns `None` for falsy input
- `src/biocurator/providers/base.py` line 106: `DatabaseConfig.retry: RetryConfig | None = None`
- Per-database merge in `src/biocurator/core/curator.py` lines 171-180:
  - `self.global_retry.resolve()` provides global defaults
  - Per-db from `search_config.retry[db_name]` overrides via `RetryConfig.resolve(base)`
  - Result assigned to `searcher.config.retry`
- **Tests:** `tests/config/test_schema.py` — 8 tests covering `SearchConfig`, `FilterConfig`, `ExportConfig`, `JobConfig`, `GlobalConfig`, `preflight_check` defaults

---

### ✅ CFG-01 — Retry/circuit breaker/timeout fields with defaults

**Evidence:**
- `src/biocurator/config/schema.py` line 154: `GlobalConfig.retry: RetryConfig | None = None` — global retry at top level, Optional
- `src/biocurator/config/schema.py` line 122: `SearchConfig.retry: dict[str, RetryConfig] | None = None` — per-database overrides, Optional with None default
- `src/biocurator/providers/base.py` line 106: `DatabaseConfig.retry: RetryConfig | None = None` — resolved at searcher init
- `src/biocurator/providers/base.py` line 105: `DatabaseConfig.timeout: int = 30` — timeout field with sensible default
- `src/biocurator/config/loader.py` line 39-40: `raw_retry = data.get("retry")` → `RetryConfig.from_dict(raw_retry) if raw_retry else None` — global retry parsing, conditional, backward compatible
- `src/biocurator/config/loader.py` lines 72-77: `raw_job_retry = search_data.get("retry")` → per-database retry parsing with `RetryConfig.from_dict()`
- `src/biocurator/config/loader.py` line 43: `GlobalConfig(email=email, jobs=jobs, retry=retry_cfg, breaker=breaker_cfg)` — config fields passed to constructor
- All new fields (`retry`, `breaker`, `timeout`) are Optional with None defaults — existing configs without these fields parse without error
- Searchers handle `retry=None`: `self.config.retry.resolve() if self.config.retry else RetryConfig.defaults()` (ncbi:48, uniprot:44-46)
- `BreakerConfig` same pattern at `schema.py:55-108` with `resolve()`, `defaults()`, `from_dict()` — but this is Phase 2 scope; the CFG-01 requirement is satisfied by the retry fields alone
- **Tests:** `tests/config/test_loader.py` — 9 tests including backward compatibility (`empty_job_section_gets_defaults`) proving configs without retry/breaker parse

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `NCBISearcher.search()` | `DatabaseSearchError` | `except Exception: raise DatabaseSearchError` | ✓ WIRED | `ncbi/searcher.py:112` |
| `UniProtSearcher.search()` | `DatabaseSearchError` | `except Exception: raise DatabaseSearchError` | ✓ WIRED | `uniprot/searcher.py:97` |
| `_make_retryer()` (ncbi) | `RETRYABLE_PREDICATE` | `retry=RETRYABLE_PREDICATE` | ✓ WIRED | `ncbi/searcher.py:56` |
| `_make_retryer()` (uniprot) | `RETRYABLE_PREDICATE` | `retry=RETRYABLE_PREDICATE` | ✓ WIRED | `uniprot/searcher.py:53` |
| `ConfigLoader._parse()` | `RetryConfig` | `RetryConfig.from_dict(raw_retry)` | ✓ WIRED | `loader.py:40` |
| `ConfigLoader._parse_job()` | `RetryConfig` (per-db) | Per-database `RetryConfig.from_dict()` | ✓ WIRED | `loader.py:72-77` |
| `run_job()` merge | `searcher.config.retry` | Per-db `resolve(base)` > global `resolve()` > defaults | ✓ WIRED | `curator.py:171-180` |
| `_safe_entrez_call` | `Retrying` via tenacity | `retryer(func, **kwargs)` + parse outside | ✓ WIRED | `ncbi/searcher.py:68-71` |
| `_safe_get` | `Retrying` via tenacity | `retryer(self.session.get, url, **kwargs)` + raise_for_status inside | ✓ WIRED | `uniprot/searcher.py:66-67` |
| Searcher fallback | `RetryConfig.defaults()` | `self.config.retry.resolve() if self.config.retry else RetryConfig.defaults()` | ✓ WIRED | `ncbi:48, uniprot:44-46` |

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/biocurator/config/schema.py` | `RetryConfig` dataclass with 4 fields + `resolve()`, `defaults()`, `from_dict()` | ✓ VERIFIED | Lines 5-52, all fields Optional with None defaults |
| `src/biocurator/providers/base.py` | `DatabaseConfig.retry` field + `timeout` field | ✓ VERIFIED | Line 106: `retry: RetryConfig \| None = None`, line 105: `timeout: int = 30` |
| `src/biocurator/config/loader.py` | Parse global + per-database retry from YAML | ✓ VERIFIED | Line 40: global, lines 72-77: per-database |
| `src/biocurator/utils/retryable_exceptions.py` | `RETRYABLE_PREDICATE` with `_is_retryable()` | ✓ VERIFIED | Line 31: predicate, lines 8-28: 5xx/network retryable, 4xx not |
| `src/biocurator/utils/network.py` | Custom `@retry` removed, comment noting migration | ✓ VERIFIED | Lines 12-13: "Custom @retry removed in Phase 1" |
| `src/biocurator/providers/ncbi/searcher.py` | tenacity Retrying at call sites, `DatabaseSearchError` in public methods | ✓ VERIFIED | Lines 9-14: tenacity imports, 68/77: Retrying calls, 112/169/226: DatabaseSearchError |
| `src/biocurator/providers/uniprot/searcher.py` | tenacity Retrying at call sites, `DatabaseSearchError` in public methods | ✓ VERIFIED | Lines 11-16: tenacity imports, 66: Retrying call, 97/152/193: DatabaseSearchError |
| `src/biocurator/core/curator.py` | Retry merge logic (per-db > global > defaults) | ✓ VERIFIED | Lines 67/78: retry passed to DatabaseConfig, 171-180: merge logic |
| `pyproject.toml` | tenacity dependency | ✓ VERIFIED | Line 38: `"tenacity>=9.1,<10.0"` |
| `src/biocurator/exceptions.py` | `DatabaseSearchError` typed exception | ✓ VERIFIED | Line 22: `class DatabaseSearchError(BiocuratorError)` |

---

## Test Results

```
$ uv run pytest tests/ -q --tb=short

........................................................................ [ 37%]
........................................................................ [ 75%]
..............................................                           [100%]
190 passed in 0.53s
```

**190/190 passed — well above the 154 minimum threshold. No regressions.**

### Per-File Breakdown

| Test File | Passed | Coverage |
|-----------|--------|----------|
| `tests/providers/ncbi/test_searcher.py` | 15 | NCBI query building (10), error behavior (5): `DatabaseSearchError` propagation, catch-and-continue |
| `tests/providers/uniprot/test_searcher.py` | 11 | UniProt query building (6), error behavior (5): `DatabaseSearchError`, 4xx passthrough, catch-and-continue |
| `tests/config/test_schema.py` | 8 | `SearchConfig`, `FilterConfig`, `ExportConfig`, `JobConfig`, `GlobalConfig`, `preflight_check` defaults |
| `tests/config/test_loader.py` | 9 | Config loading, backward compatibility, preflight_check parsing |
| `tests/utils/test_network.py` | 11 | Retryable exception classification |
| Other test files (Phase 2+) | 136 | Circuit breaker, health, checksums, manifests, CLI commands, streaming curation |
| **Total** | **190** | Full suite passes with zero failures |

---

## Anti-Patterns Found

None — all code patterns align with CONTEXT.md decisions:

- ✅ `Entrez.read()` happens OUTSIDE the `Retrying` block in NCBI `_safe_entrez_call()` (line 68-71): only the HTTP call is retried, parse errors are not
- ✅ `raise_for_status()` happens INSIDE the `Retrying` block in UniProt `_safe_get()` (line 66-67): 5xx responses trigger retry, 4xx are filtered by `RETRYABLE_PREDICATE`
- ✅ Config without retry blocks parses: `resolver()` handles `retry = None` → falls back to hardcoded defaults (3, 2.0, 60, 30)
- ✅ Custom `@retry` removal left no broken imports — `network.py` is clean with only documentation comments
- ✅ `DatabaseSearchError` not double-wrapped: both searchers use `except DatabaseSearchError: raise` before the generic `except Exception: raise DatabaseSearchError(...)`
- ✅ `_make_retryer()` is a DRY helper used consistently by both searchers — identical structure, no copy-paste drift

---

## Data-Flow Trace

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|-------------------|--------|
| Searcher retry config | `self.config.retry` | `DatabaseConfig(retry=...)` from `curator.py` merge | ✓ Yes — resolved RetryConfig flows to `_make_retryer()` | ✓ FLOWING |
| `_make_retryer()` output | `Retrying(...)` | `RetryConfig` fields mapped to tenacity params | ✓ Yes — `stop`, `wait`, `retry`, `before_sleep` all configured | ✓ FLOWING |
| `RETRYABLE_PREDICATE` | `retry_if_exception(_is_retryable)` | `retryable_exceptions.py` | ✓ Yes — custom predicate filtering 4xx/5xx/network errors | ✓ FLOWING |
| `ConfigLoader._parse()` retry | `GlobalConfig.retry` | YAML `retry:` block | ✓ Yes — parsed via `RetryConfig.from_dict()`, flows to `Biocurator.__init__` | ✓ FLOWING |
| `ConfigLoader._parse_job()` retry | `SearchConfig.retry` | YAML `search.retry:` block | ✓ Yes — per-db dict parsed, flows to `run_job()` merge | ✓ FLOWING |

---

## Behavioral Spot-Checks

| Behavior | Result | Status |
|----------|--------|--------|
| `DatabaseSearchError` typed exception exists | `class DatabaseSearchError(BiocuratorError)` at `exceptions.py:22` | ✓ PASS |
| NCBI `search()` raises on network failure | `test_search_raises_database_search_error_on_network_failure` passes | ✓ PASS |
| UniProt `search()` raises on HTTP 400 | `test_search_raises_database_search_error_on_http_400` passes | ✓ PASS |
| NCBI `fetch_metadata()` continues on batch failure | `test_fetch_metadata_continues_on_batch_failure` passes (empty result, no crash) | ✓ PASS |
| UniProt `download()` continues on single failure | `test_download_continues_on_single_failure` passes (empty result, no crash) | ✓ PASS |
| Config without retry block parses | `test_empty_job_section_gets_defaults` passes | ✓ PASS |
| `RetryConfig.defaults()` returns populated values | `defaults().max_attempts == 3`, `defaults().backoff_factor == 2.0` | ✓ PASS |
| Custom `@retry` removed from `network.py` | File contains only docstring + comment, no decorator code | ✓ PASS |
| tenacity in pyproject.toml | `tenacity>=9.1,<10.0` at line 38 | ✓ PASS |
| All 190 tests pass | 190 passed in 0.53s | ✓ PASS |

---

_Verified: 2026-05-25T19:44:00Z_
_Verifier: Claude (GSD executor — retrospective audit)_
_Audit basis: CONTEXT.md decisions, Phase 01 plan summaries (01-01, 01-02, 01-03), 01-UAT.md, and live codebase inspection_
