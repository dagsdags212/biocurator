# Phase 1: Error Handling & Retry Foundation — Discussion Context

## Phase Goal
Exceptions propagate clearly instead of silent empty results; retry uses tenacity with configurable per-provider settings; config schema accepts all new fields.

## Requirements Addressed
ERR-01, ERR-02, ERR-03, ERR-04, CFG-01, CFG-02

## Domain Overview
The existing CLI tool has working search/fetch/download/export pipelines for NCBI (via Biopython Bio.Entrez) and UniProt (via requests). The two major issues are: (1) API exceptions are silently caught with `except Exception: return []`, so users never know when a search fails; (2) the custom `@retry` decorator has no configurability, no backoff reporting, and no exception narrowing.

## Decisions

### 1. Error Surface Behavior

**Generators (fetch_metadata, download):** Collect errors per-record, log warning, continue with remaining records. Report failure summary at end. Never silently skip.

**search() methods:** Raise typed exception (`DatabaseSearchError`) instead of returning `[]`. Let the error propagate to the CLI handler for clear user feedback.

**Why:** Fail-fast in search (a failed search means zero results — no point continuing). Collect-and-continue in batch operations (partial results are useful; don't throw away 99 good records because 1 failed).

### 2. Exception Classification

**Retryable (tenacity):** Only network-level exceptions:
- `urllib.error.URLError`, `urllib.error.HTTPError` (NCBI via Biopython)
- `requests.ConnectionError`, `requests.Timeout`, `requests.HTTPError` with 5xx status (UniProt via requests)
- `socket.timeout`, `socket.gaierror`

**Non-retryable (fail immediately):** Parse/data errors:
- `ValueError`, `KeyError`, `TypeError`
- XML/JSON parse errors from Biopython or responses
- `requests.HTTPError` with 4xx status (bad request, auth error — retrying won't help)

### 3. Migration Strategy

Full replacement: remove the custom `@retry` decorator from `utils/network.py` entirely. Replace all 3 call sites with `tenacity` decorators using consistent, configured parameters.

**Call sites:**
- `NCBISearcher._safe_entrez_call` — wraps `Bio.Entrez` calls
- `UniProtSearcher._safe_get` — wraps `requests.get`
- `NCBI download` inline `_fetch()` — nested retry

### 4. Config Structure

**Where:** Global defaults at top level of YAML + per-database overrides inside job search config.

**Fields (user-friendly names):**
- `max_attempts`: int (default 3) — max retry attempts
- `backoff_factor`: float (default 2.0) — exponential backoff multiplier (tenacity's `wait_exponential`)
- `max_delay`: int (default 60) — max delay in seconds between retries
- `timeout`: int (default 30) — request timeout in seconds

**YAML shape:**
```yaml
email: user@example.com
retry:
  max_attempts: 3
  backoff_factor: 2.0
  max_delay: 60
  timeout: 30
jobs:
  my_job:
    search:
      databases: ["ncbi", "uniprot"]
      organism: "Homo sapiens"
      keywords: ["COX1"]
      retry:
        ncbi:
          max_attempts: 5  # override for NCBI only
```

### 5. Field Naming

User-friendly names in config YAML. Map to tenacity internally:
- `max_attempts` → `stop=stop_after_attempt(n)`
- `backoff_factor` → `wait=wait_exponential(multiplier=n)`
- `max_delay` → `wait=wait_exponential(max=n)`
- `timeout` → not tenacity — passed to `requests.get(timeout=n)` or `Bio.Entrez.email` context

## Key Constraints

1. **Backward compatibility** — existing configs without retry/breaker/timeout fields must parse without error (all new fields are optional with defaults)
2. **ERR-01 first** — silent error swallowing fix must be implemented before any other enhancement; it's the prerequisite for all downstream reliability work
3. **Typed exceptions** — must distinguish network errors (transient, retryable) from data/parse errors (permanent, not retryable)
4. **Logging** — retry attempts must show attempt number and backoff timing in logs
5. **No new external services** — all must work offline except the database API calls themselves

## Architecture Guidance

- Add tenacity to dependencies in `pyproject.toml`
- Remove `utils/network.py` custom `@retry` (or keep only `RetryConfig` dataclass if still useful)
- Extend `DatabaseConfig` in `providers/base.py` with retry fields
- Extend `SearchConfig` in `config/schema.py` with optional `retry: dict[str, RetryConfig]` for per-database overrides
- Extend `GlobalConfig` with optional `retry: RetryConfig` for global defaults
- Merge logic: job per-database override > global per-database defaults (if we had them) > global retry defaults > tenacity defaults
- Raise `DatabaseSearchError` in search methods; let generators continue on error but collect warnings

## Relevant Files

- `src/biocurator/providers/ncbi/searcher.py` — NCBI silent error swallowing at line 74
- `src/biocurator/providers/uniprot/searcher.py` — UniProt silent error swallowing at line 53
- `src/biocurator/utils/network.py` — custom @retry decorator (80 lines, 3 call sites)
- `src/biocurator/providers/base.py` — DatabaseConfig, DatabaseSearcher ABC
- `src/biocurator/config/schema.py` — GlobalConfig, SearchConfig, database_configs dataclasses
- `src/biocurator/config/loader.py` — ConfigLoader._parse() and _parse_job()
- `src/biocurator/exceptions.py` — Exception hierarchy (add types as needed)
- `pyproject.toml` — add tenacity dependency
