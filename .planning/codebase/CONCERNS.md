# Codebase Concerns

**Analysis Date:** 2025-05-25

## Tech Debt

### Dead comment referencing removed method (LOW)
- **Issue:** `src/biocurator/core/curator.py` line 170 contains `# _export is no longer needed as StreamingExporter handles it.` — a stale comment referencing a method that has been removed.
- **Files:** `src/biocurator/core/curator.py`
- **Impact:** Minor confusion for future readers.
- **Fix approach:** Remove the commented reference.

### Standalone `main.py` entry point unused (LOW)
- **Issue:** `/home/dagsdags/workspace/personal-projects/biocurator/main.py` is a standalone script that duplicates the Python API example from the README. It creates a `Biocurator` with a hardcoded email `"your@email.com"` and is not registered as an entry point. It cannot be meaningfully run.
- **Files:** `main.py`
- **Impact:** Dead file that could confuse new contributors.
- **Fix approach:** Remove or convert into a proper example script.

### Duplicate logic between `run_job` and `preview_command` (MEDIUM)
- **Issue:** The `common_kwargs` dictionary construction is duplicated verbatim between `src/biocurator/core/curator.py` (lines 95–109) and `src/biocurator/cli/commands/preview.py` (lines 54–68). The same `db_name == "ncbi"` / `== "uniprot"` branching is also duplicated.
- **Files:** `src/biocurator/core/curator.py`, `src/biocurator/cli/commands/preview.py`
- **Impact:** Any change to the criteria construction must be updated in two places. This has already caused subtle bugs (see CHANGELOG v0.1.1 for a similar issue).
- **Fix approach:** Extract criteria construction into a shared factory method on `Biocurator` or a helper function.

### `SequenceFilter` class is all static methods (LOW)
- **Issue:** `src/biocurator/core/filters.py` `SequenceFilter` has 7 public/private methods, all `@staticmethod`. It functions as a namespace, not a class.
- **Files:** `src/biocurator/core/filters.py`
- **Impact:** Minor; doesn't prevent usage but the class wrapper is unnecessary.
- **Fix approach:** Convert to module-level functions.

### `_json_count` initialized via `hasattr` pattern (MEDIUM)
- **Issue:** In `src/biocurator/core/exporter.py` line 98–99, `_json_count` is lazily initialized via `if not hasattr(self, "_json_count")`. This is fragile — the attribute should be initialized in `__init__` alongside the other counters.
- **Files:** `src/biocurator/core/exporter.py`
- **Impact:** If `__init__` is ever refactored to use `__slots__` or if serialization methods reset object state, this breaks silently.
- **Fix approach:** Initialize `self._json_count = 0` in `__init__`.

### Empty `__init__.py` files (LOW)
- **Issue:** Multiple `__init__.py` files are completely empty: `src/biocurator/utils/__init__.py`, `src/biocurator/core/__init__.py`, `src/biocurator/config/__init__.py`, `src/biocurator/cli/commands/__init__.py`, and all `tests/*/__init__.py`.
- **Files:** Multiple `__init__.py` files
- **Impact:** No impact on functionality, but inconsistency — `src/biocurator/providers/__init__.py` is populated while `src/biocurator/core/__init__.py` is empty.
- **Fix approach:** Optionally consolidate top-level exports through `src/biocurator/__init__.py`.

---

## Reliability Issues

### Silent error swallowing in all searchers (HIGH)
- **Issue:** Both `NCBISearcher` and `UniProtSearcher` wrap all public methods (`search`, `fetch_metadata`, `download`) in broad `except Exception` blocks that log a warning and return empty results / skip failures:
  - `src/biocurator/providers/ncbi/searcher.py:62`: `except Exception ... return []`
  - `src/biocurator/providers/ncbi/searcher.py:107`: `except Exception ... logger.warning(...)` — silently skips failed batches
  - `src/biocurator/providers/ncbi/searcher.py:163`: `except Exception ... logger.warning(...)` — silently skips failed downloads
  - `src/biocurator/providers/uniprot/searcher.py:53`: `except Exception ... return []`
  - `src/biocurator/providers/uniprot/searcher.py:87`: `except Exception ... logger.warning(...)` — silently skips failed batches
  - `src/biocurator/providers/uniprot/searcher.py:108`: `except Exception ... logger.warning(...)` — silently skips failed downloads
- **Impact:** Partial data loss without user visibility. If a batch fails during metadata fetch, the user gets no indication that data is missing. A network blip in the middle of a 500-sequence download silently drops records.
- **Fix approach:**
  - `search()` should distinguish between "no results" and "error" (return empty list vs raise)
  - `fetch_metadata()` and `download()` should track and report failure counts
  - Propagate critical errors (auth failures, rate limits) instead of swallowing them

### `retry` decorator catches all `Exception` (MEDIUM)
- **Issue:** `src/biocurator/utils/network.py` defaults `exceptions=(Exception,)` — the most general exception class. This means `KeyboardInterrupt`, `MemoryError`, or programming bugs like `AttributeError` would trigger retries before eventually failing.
- **Files:** `src/biocurator/utils/network.py`
- **Impact:** Retrying non-recoverable errors wastes time and masks real problems.
- **Fix approach:** Use narrower exception types (`requests.RequestException`, `IOError`, `ValueError`) or at minimum catch `Exception` but not `BaseException`.

### `filter_by_criteria` truthiness check on `min_length`/`max_length` (MEDIUM)
- **Issue:** In `src/biocurator/core/filters.py` lines 46 and 54, `if criteria.min_length:` and `if criteria.max_length:` use truthiness. If `min_length=0` (a valid biological value meaning "any length"), the filter is skipped. While 0-length sequences are rare, this is semantically incorrect.
- **Files:** `src/biocurator/core/filters.py`
- **Impact:** `min_length=0` would be silently ignored instead of passing all sequences.
- **Fix approach:** Use `if criteria.min_length is not None:` consistently.

### Quality score heuristic may misclassify sequences (LOW)
- **Issue:** `src/biocurator/core/filters.py` `__calculate_quality_score()` line 168 checks `if any(base in seq_str for base in "ATGC"):` to detect nucleotide sequences. Any random uppercase string containing A, T, G, or C will be treated as a nucleotide sequence. Similarly, line 173 checks for protein by looking for any single amino acid letter.
- **Files:** `src/biocurator/core/filters.py`
- **Impact:** Protein sequences high in A, T, G, or C content would have both nucleotide and protein penalties applied, potentially scoring below threshold.
- **Fix approach:** Use `sequence_type` metadata from the record or a more robust heuristic (e.g., length divisible by 3 for coding sequences, or explicit database field).

### CSV export creates per-record DataFrames (MEDIUM)
- **Issue:** `src/biocurator/core/exporter.py` lines 90–93 create a new `pd.DataFrame` for each record and append via `to_csv(mode='a')`. This is extremely inefficient — each call creates a DataFrame, serializes to CSV, and writes.
- **Files:** `src/biocurator/core/exporter.py`
- **Impact:** For thousands of sequences, this creates unnecessary GC pressure and I/O overhead. Pandas DataFrames are designed for batch operations.
- **Fix approach:** Buffer records and flush in batches, or use Python's `csv.DictWriter` directly (no pandas needed for append-mode CSV).

### NCBI `_safe_entrez_call` wraps non-retryable errors (LOW)
- **Issue:** `src/biocurator/providers/ncbi/searcher.py` line 30 uses `@retry(exceptions=(Exception,), max_attempts=3)` on `_safe_entrez_call`. The `Entrez.read()` call inside could fail for non-retryable reasons (XML parse errors, schema mismatches) which would still be retried 3 times.
- **Files:** `src/biocurator/providers/ncbi/searcher.py`
- **Impact:** Wasted time on obviously non-recoverable parse errors.
- **Fix approach:** Separate connection retries from parse errors.

---

## Security Concerns

### API key stored in plaintext dataclass (MEDIUM)
- **Issue:** `src/biocurator/providers/base.py` `DatabaseConfig.api_key` is `str | None` — a plaintext field. There is no mechanism to load API keys from environment variables or a secrets store. The NCBI API key must be written directly into the config YAML file.
- **Files:** `src/biocurator/providers/base.py`, `src/biocurator/config/schema.py`, `src/biocurator/config/loader.py`
- **Impact:** Users may accidentally commit API keys to version control in their config files.
- **Fix approach:**
  - Support `env:` prefix in config values (e.g., `api_key: "env:NCBI_API_KEY"`)
  - Add a note in the template about using environment variables
  - Optionally use `SecretStr` type to prevent accidental logging

### Sensitive data filter is rudimentary (LOW)
- **Issue:** `src/biocurator/utils/logging.py` `_SensitiveFilter` checks for any log message containing "password", "token", "key", or "secret" in lowercase and redacts the entire message. This is overly broad (may redact legitimate messages containing "key" like "query_key") and misses patterns (API keys that log without those keywords).
- **Files:** `src/biocurator/utils/logging.py`
- **Impact:** Some API key leaks may not be caught; some legitimate logs may be redacted.
- **Fix approach:** Use regex-based pattern matching for common API key formats, or annotate sensitive fields directly.

### Email hardcoded in config and committed (MEDIUM)
- **Issue:** `/home/dagsdags/workspace/personal-projects/biocurator/config.yaml` contains a real email address (`jegsamson.dev@gmail.com`) committed to the repository. This is used as the NCBI Entrez email parameter.
- **Files:** `config.yaml`
- **Impact:** Email exposed in version control. If the email becomes invalid, NCBI will block requests from this address.
- **Fix approach:** Use a placeholder like `your@email.com` in the committed config, document that users must provide their own email.

### No Config validation for input data (MEDIUM)
- **Issue:** The config loader (`src/biocurator/config/loader.py`) performs minimal validation — only checks `email` is present and `databases` is non-empty. There is no validation of `organism`, `keywords`, `date_range` format, or other fields before they are used in API queries.
- **Files:** `src/biocurator/config/loader.py`
- **Impact:** Malformed dates (`"not-a-date"`) cause runtime errors deep in filtering logic (caught by `ValueError` at runtime, but no upfront validation). Invalid organism names result in empty API responses with no user feedback.
- **Fix approach:** Add Pydantic or similar validation, or at minimum validate date formats and numeric ranges at load time.

---

## Performance Risks

### Sequential one-record-at-a-time NCBI download (MEDIUM)
- **Issue:** `src/biocurator/providers/ncbi/searcher.py` `download()` fetches one sequence at a time via `efetch` with `retmax=1`. NCBI's E-utilities supports batch fetching (up to 500 at once for FASTA). The current approach multiplies API calls and wall-clock time.
- **Files:** `src/biocurator/providers/ncbi/searcher.py`
- **Impact:** A 500-sequence download takes 500 API calls instead of ~1-2. With `rate_limit=0.3`, that's 150 seconds vs potentially < 5 seconds.
- **Fix approach:** Batch download with `retmax=batch_size` and iterate over multi-record FASTA responses using `SeqIO.parse()` instead of `SeqIO.read()`.

### UniProt download is one-at-a-time (MEDIUM)
- **Issue:** `src/biocurator/providers/uniprot/searcher.py` `download()` makes one HTTP request per UniProt ID. UniProt REST API supports batch downloads via `POST /uniprotkb/accessions` or `GET /uniprotkb/stream`.
- **Files:** `src/biocurator/providers/uniprot/searcher.py`
- **Impact:** Same as NCBI — unnecessary API round-trips.
- **Fix approach:** Batch multiple IDs into a single request.

### Redundant list copying in `filter_by_criteria` (LOW)
- **Issue:** `src/biocurator/core/filters.py` `filter_by_criteria()` copies the sequence list at the start (`filtered = sequences.copy()`) and creates a new list for each filter operation via `filter()` and `list()`. For large datasets, this creates O(n) temporary lists per filter.
- **Files:** `src/biocurator/core/filters.py`
- **Impact:** Minor for typical datasets, but wastes memory for large collections.
- **Fix approach:** Use generator chains or single-pass filtering.

### CSV export creates per-row DataFrames (MEDIUM)
- **Issue:** Already documented under Reliability — each CSV row creates a new `pd.DataFrame`. For 10,000 records, this allocates and GCs 10,000 small DataFrames plus 10,000 `to_csv` invocations.
- **Files:** `src/biocurator/core/exporter.py`
- **Impact:** Noticeable slowdown at scale. CSV writing would dominate total runtime.
- **Fix approach:** Use `csv.DictWriter` with buffering, or batch rows into larger DataFrame writes.

---

## Maintainability Issues

### `run_job` method is too long (MEDIUM)
- **Issue:** `src/biocurator/core/curator.py` `run_job()` is ~108 lines and handles search, criteria construction, streaming, filtering, downloading, and progress reporting in a single method. It has three levels of nested logic (job loop + record loop + filter loop).
- **Files:** `src/biocurator/core/curator.py`
- **Impact:** Hard to test, hard to extend (e.g., adding a new database type requires modifying this method).
- **Fix approach:** Extract per-database criteria construction, per-record filtering, and download orchestration into separate methods.

### `StreamingExporter` mixes multiple concerns (MEDIUM)
- **Issue:** `src/biocurator/core/exporter.py` `StreamingExporter` handles three formats (FASTA, CSV, JSON) in a single class with `if "fasta"` / `if "csv"` / `if "json"` branching throughout. Adding a new format (e.g., GenBank, GFF) means modifying multiple methods.
- **Files:** `src/biocurator/core/exporter.py`
- **Impact:** Violates Open/Closed principle. Format-specific logic leaks across `open()`, `write_record()`, and `close()`.
- **Fix approach:** Use a strategy/visitor pattern where each format is a separate writer class registered by format name.

### `PreviewCommand` uses local import pattern (LOW)
- **Issue:** `src/biocurator/cli/commands/preview.py` line 71 imports `NCBIDatabase` inside the function body with `from biocurator.providers.base import NCBIDatabase as _NCBIDb`. This is inconsistent with the module-level imports and the `as _NCBIDb` alias suggests it was needed to avoid a name collision that doesn't exist.
- **Files:** `src/biocurator/cli/commands/preview.py`
- **Impact:** Confusing pattern; increases cognitive load. The same pattern exists in `curator.py` line 111.
- **Fix approach:** Move import to module level. If there's no import collision, remove the alias.

### Test stubs have incompatible return types (LOW)
- **Issue:** In `tests/providers/test_registry.py`, the `_FakeSearcher` class returns `list[dict[str, Any]]` from `fetch_metadata` and `download`, but the abstract base class declares `Iterator[SequenceRecord]`. These stubs would fail type checking.
- **Files:** `tests/providers/test_registry.py`
- **Impact:** Type checker warnings. Test doubles drifting from the real interface.
- **Fix approach:** Update stubs to match the correct return types.

---

## Testing Gaps

### `SequenceFilter` is entirely untested (HIGH)
- **Issue:** `src/biocurator/core/filters.py` (324 lines, the largest file in the project) has zero dedicated tests. There are no tests for `filter_by_criteria`, `apply_quality_filter`, `__calculate_quality_score`, `remove_duplicates`, `filter_by_taxonomy`, or `filter_by_date_range`.
- **Files:** `src/biocurator/core/filters.py`
- **Impact:** All filtering logic — the core value proposition of the application — is untested. This is where multiple v0.1.1 bugs were found (organism filter, quality filter, length field mismatch).
- **Priority:** HIGH

### `StreamingExporter` has no independent tests (MEDIUM)
- **Issue:** `src/biocurator/core/exporter.py` `StreamingExporter` is tested only indirectly through `test_curator.py` and `test_streaming_curation.py`. There are no unit tests for the exporter in isolation — no tests for partial writes, edge cases with missing sequences, or concurrent format output.
- **Files:** `src/biocurator/core/exporter.py`
- **Impact:** Format-specific bugs (e.g., malformed JSON for multiple records, CSV header issues) are not caught at the unit level.

### No integration tests for network operations (MEDIUM)
- **Issue:** All tests use `MagicMock` to mock searchers. There are no integration tests that actually call NCBI or UniProt APIs (even against a test endpoint). The `tests/providers/ncbi/test_searcher.py` only tests `build_query()` delegation, never `search()`, `fetch_metadata()`, or `download()`.
- **Files:** `tests/providers/ncbi/test_searcher.py`, `tests/providers/uniprot/test_searcher.py`
- **Impact:** API contract changes, network error handling, rate limiting, and response parsing are never validated. An NCBI API change would silently break the application.

### No `conftest.py` (LOW)
- **Issue:** No `conftest.py` file exists in any test directory. Fixtures are defined per test module, leading to duplication (several tests create similar `MagicMock` searcher fixtures).
- **Files:** Project-wide
- **Impact:** Test fixture setup is duplicated across files. Adding a shared `conftest.py` would reduce boilerplate.

### Error handling paths are untested (MEDIUM)
- **Issue:** The `except Exception` pathways in both NCBI and UniProt searchers are never tested. There are no tests that simulate network failures, API errors, or malformed responses to verify graceful degradation.
- **Files:** All searcher test files
- **Impact:** Error handling may have bugs or unexpected behavior that only surfaces in production.

### No coverage configuration (LOW)
- **Issue:** No `pyproject.toml` `[tool.coverage.*]` section or `.coveragerc` file. Coverage is neither configured nor enforced.
- **Files:** `pyproject.toml`
- **Impact:** Cannot objectively measure test coverage. No safety net for untested code.

---

## Dependency Risks

### Requires Python 3.13+ only (MEDIUM)
- **Issue:** `pyproject.toml` specifies `requires-python = ">=3.13"`. Python 3.13 was released in October 2025 and is very new. Many bioinformatics environments (HPC clusters, institutional servers, CI runners) may still be on 3.12 or 3.11.
- **Files:** `pyproject.toml`
- **Impact:** Severely limits adoption. No fallback for environments that don't have 3.13 yet.
- **Fix approach:** Test and support Python 3.12+ or 3.11+.

### pandas>=3.0.3 — very new major version (MEDIUM)
- **Issue:** `pandas>=3.0.3` pins to a very recent major version (pandas 3.x was released in 2025). There may be stability issues, breaking changes in minor releases, or compatibility problems with older `numpy` versions.
- **Files:** `pyproject.toml`
- **Impact:** If a user's environment has pandas 2.x pinned by another dependency, installation conflicts arise. Pandas 3.x may have regressions.
- **Fix approach:** Consider `pandas>=2.0,<4.0` to maintain compatibility with stable pandas 2.x while allowing 3.x.

### No `httpx` dependency — synchronous only (LOW)
- **Issue:** Uses `requests` library for HTTP calls. `httpx` would provide async support and better connection pooling. For a streaming application that makes many sequential API calls, async could reduce overhead.
- **Files:** `pyproject.toml`
- **Impact:** Not a current issue, but would block future async streaming performance improvements.
- **Fix approach:** Add `httpx` as an optional dependency when async support is needed.

### Missing type stubs for test dependencies (LOW)
- **Issue:** `pytest` and `pytest-mock` dev dependencies have no type stubs declared. Type checkers will fall back to `Any`.
- **Files:** `pyproject.toml`
- **Impact:** Reduced type safety in test code.

---

## API Contract Risks

### NCBI E-utilities API version is implicit (MEDIUM)
- **Issue:** NCBI API calls use implicit default API version (no `retmode` versioning, no Accept headers). NCBI E-utilities occasionally changes response formats (XML schema changes, field deprecations). The application does not pin or check API versions.
- **Files:** `src/biocurator/providers/ncbi/searcher.py`
- **Impact:** If NCBI changes the XML response format or deprecates fields used by `Entrez.read()`, the application silently breaks. The `_safe_entrez_call` retry would retry parse failures 3 times before giving up.

### UniProt REST API implicit versioning (MEDIUM)
- **Issue:** `src/biocurator/providers/uniprot/searcher.py` uses unversioned UniProt REST API endpoints (`/uniprotkb/search`, `/uniprotkb/accessions`). UniProt has deprecated endpoints in the past (e.g., legacy `uniprot.org` → `rest.uniprot.org` migration).
- **Files:** `src/biocurator/providers/uniprot/searcher.py`
- **Impact:** Same as NCBI — unannounced API changes could break the application.

### `SequenceRecord` dataclass lacks versioning (LOW)
- **Issue:** The `SequenceRecord` dataclass is the core data contract passed through the pipeline. Adding or removing fields requires coordinated changes across multiple searchers, filters, and exporters.
- **Files:** `src/biocurator/providers/base.py`
- **Impact:** Changes to the data contract are fragile and require changes in many places.

---

## Scalability Concerns

### In-memory metadata aggregation before filtering (MEDIUM)
- **Issue:** `src/biocurator/core/curator.py` `run_job()` collects all metadata into `filtered_metadata_ids` (line 139) before starting downloads. For searches returning millions of IDs, this list could be large.
- **Files:** `src/biocurator/core/curator.py`
- **Impact:** Memory grows linearly with search result size. The streaming architecture only applies to downloads, not metadata filtering.
- **Fix approach:** Apply metadata filtering at the query level where possible, or stream/process metadata in batches.

### No pagination beyond `max_results` (LOW)
- **Issue:** NCBI's `esearch` uses `retmax=criteria.max_results`. There is no pagination to fetch "more than `max_results`" results. Users who need 10,000+ sequences must run multiple jobs.
- **Files:** `src/biocurator/providers/ncbi/searcher.py`
- **Impact:** No way to get complete large datasets in a single job.
- **Fix approach:** Add a `use_history=True` loop with `retstart`/`retmax` paging to fetch all results in batches.

### No progress reporting for individual slow downloads (LOW)
- **Issue:** The progress reporting in `run_job()` reports at the batch level for metadata but at the per-record level for downloads. For individual slow downloads (e.g., large genomic sequences), there is no intermediate progress.
- **Files:** `src/biocurator/core/curator.py`
- **Impact:** Users cannot distinguish between a slow download and a stuck process.

---

## Documentation Gaps

### Missing docstrings in searcher `__init__` methods (LOW)
- **Issue:** `NCBISearcher.__init__` (`src/biocurator/providers/ncbi/searcher.py:23`) and `UniProtSearcher.__init__` (`src/biocurator/providers/uniprot/searcher.py:23`) have no docstrings explaining the `config` and `email` parameters.
- **Files:** `src/biocurator/providers/ncbi/searcher.py`, `src/biocurator/providers/uniprot/searcher.py`
- **Impact:** Minor — init parameters are somewhat self-explanatory but inconsistent with the well-documented methods elsewhere.

### `main.py` has no module docstring (LOW)
- **Issue:** `/home/dagsdags/workspace/personal-projects/biocurator/main.py` has no module-level docstring or explanation of its purpose.
- **Files:** `main.py`
- **Impact:** Unclear whether this is an example, entry point, or development utility.

---

## Summary of Priority Issues

| Priority | Area | Issue |
|----------|------|-------|
| **HIGH** | Testing | `SequenceFilter` (324 lines) is entirely untested |
| **HIGH** | Reliability | All searchers silently swallow exceptions and return empty data |
| **MEDIUM** | Performance | CSV export creates per-row DataFrames (O(n) overhead) |
| **MEDIUM** | Performance | NCBI/UniProt downloads are one-at-a-time instead of batched |
| **MEDIUM** | Security | API keys stored in plaintext with no env-var support |
| **MEDIUM** | Security | Real email address committed in `config.yaml` |
| **MEDIUM** | Dependencies | Requires Python 3.13+ only (no 3.12 support) |
| **MEDIUM** | Dependencies | pandas>=3.0.3 — very new, potentially unstable |
| **MEDIUM** | Maintainability | `run_job()` is 108 lines with nested logic |
| **MEDIUM** | Maintainability | Duplicate criteria construction logic in curator and preview |
| **MEDIUM** | Reliability | Truthiness check on `min_length`/`max_length` (0 treated as falsy) |
| **MEDIUM** | Reliability | Retry decorator catches all `Exception`, including non-recoverable |
| **MEDIUM** | Testing | No integration tests for network operations |
| **MEDIUM** | Testing | Error handling paths are untested |
| **MEDIUM** | API Contract | NCBI/UniProt API versions are implicit |
| **MEDIUM** | Scalability | Metadata fully loaded into memory before download |
| **LOW** | Various | Minor code smells, empty `__init__.py`, stale comments |

---

*Concerns audit: 2025-05-25*
