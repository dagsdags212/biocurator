# Phase 1: Error Handling & Retry Foundation — Pattern Map

**Mapped:** 2026-05-25
**Files analyzed:** 9 (4 modified config/schema, 4 modified providers, 1 removed utility)
**Analogs found:** 9 / 9

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/biocurator/config/schema.py` | config | CRUD | `src/biocurator/config/schema.py` (itself) | exact |
| `src/biocurator/config/loader.py` | config | CRUD | `src/biocurator/config/loader.py` (itself) | exact |
| `src/biocurator/providers/base.py` | config | CRUD | `src/biocurator/providers/base.py` (itself) | exact |
| `src/biocurator/providers/ncbi/searcher.py` | service | CRUD + streaming | `src/biocurator/providers/ncbi/searcher.py` (itself) | exact |
| `src/biocurator/providers/uniprot/searcher.py` | service | CRUD + streaming | `src/biocurator/providers/uniprot/searcher.py` (itself) | exact |
| `src/biocurator/utils/network.py` | utility | request-response | `src/biocurator/utils/network.py` (being removed) | exact |
| `src/biocurator/exceptions.py` | utility | CRUD | `src/biocurator/exceptions.py` (itself) | exact |
| `pyproject.toml` | config | — | `pyproject.toml` (itself) | exact |

## Pattern Assignments

### `src/biocurator/config/schema.py` (config, CRUD)

**Analog:** `src/biocurator/config/schema.py` (existing file)

**Imports pattern** (line 1):
```python
from dataclasses import dataclass, field
```
No external imports beyond `dataclasses`. Add `RetryConfig` to this same file (per RESEARCH.md recommendation to keep all schema types in one place).

**Dataclass pattern for RetryConfig** (follow lines 4-14, 17-22):
```python
@dataclass
class SearchConfig:
    databases: list[str]
    organism: str | None = None
    # ... existing fields ...
```

**New RetryConfig dataclass** (follow same convention as `DatabaseConfig` in `base.py` lines 94-101):
```python
@dataclass
class RetryConfig:
    """Configurable retry policy with exponential backoff.

    Maps to tenacity parameters:
      max_attempts -> stop=stop_after_attempt(n)
      backoff_factor -> wait=wait_exponential(multiplier=n)
      max_delay -> wait=wait_exponential(max=n)
      timeout -> passed to requests/Entrez calls (not tenacity)
    """
    max_attempts: int = 3
    backoff_factor: float = 2.0
    max_delay: int = 60
    timeout: int = 30

    @classmethod
    def defaults(cls) -> "RetryConfig":
        return cls()
```

**Adding optional `retry` to existing dataclasses** (pattern: `None` default for backward compatibility):

`GlobalConfig` (schema.py line 41-43) — add `retry: RetryConfig | None = None`:
```python
@dataclass
class GlobalConfig:
    email: str
    jobs: list[JobConfig]
    retry: RetryConfig | None = None  # NEW — global defaults
```

`SearchConfig` (schema.py lines 4-14) — add `retry: dict[str, RetryConfig] | None = None`:
```python
@dataclass
class SearchConfig:
    databases: list[str]
    organism: str | None = None
    sequence_type: str = "nucleotide"
    keywords: list[str] = field(default_factory=list)
    max_results: int = 100
    date_range: dict | None = None
    exclude_terms: list[str] = field(default_factory=list)
    location: str | None = None
    taxonomy_filter: str | None = None
    retry: dict[str, RetryConfig] | None = None  # NEW — per-database overrides
```

---

### `src/biocurator/config/loader.py` (config, CRUD)

**Analog:** `src/biocurator/config/loader.py` (existing file)

**Imports pattern** (lines 1-10):
```python
from pathlib import Path
import yaml
from biocurator.config.schema import (
    ExportConfig,
    FilterConfig,
    GlobalConfig,
    JobConfig,
    SearchConfig,
    RetryConfig,  # NEW import
)
from biocurator.exceptions import ConfigNotFoundError, InvalidConfigError
```

**YAML parsing pattern** (lines 20-24) — `yaml.safe_load` already used. Unknown keys are silently ignored, ensuring backward compatibility.

**_parse() retry block extraction** (follow lines 27-37 pattern):
```python
@staticmethod
def _parse(data: dict) -> GlobalConfig:
    if not isinstance(data, dict):
        raise InvalidConfigError("Config must be a YAML mapping")
    email = data.get("email")
    if not email:
        raise InvalidConfigError("'email' is required at the top level")
    raw_jobs = data.get("jobs")
    if not raw_jobs or not isinstance(raw_jobs, dict):
        raise InvalidConfigError("'jobs' must be a non-empty mapping")
    jobs = [ConfigLoader._parse_job(name, job) for name, job in raw_jobs.items()]

    # NEW: parse global retry block
    raw_retry = data.get("retry")
    retry_cfg = RetryConfig(**raw_retry) if raw_retry else None

    return GlobalConfig(email=email, jobs=jobs, retry=retry_cfg)
```

**_parse_job() search retry extraction** (follow lines 40-78 pattern):
```python
# After building search_cfg (line 61), add retry parsing:
raw_job_retry = search_data.get("retry")
if raw_job_retry and isinstance(raw_job_retry, dict):
    per_db_retry = {}
    for db_name, db_retry_cfg in raw_job_retry.items():
        per_db_retry[db_name] = RetryConfig(**db_retry_cfg)
    search_cfg.retry = per_db_retry
```

---

### `src/biocurator/providers/base.py` (config, CRUD)

**Analog:** `src/biocurator/providers/base.py` (existing file)

**Imports pattern** (lines 1-5):
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Generic, TypeVar, Iterator
```

**Adding retry to DatabaseConfig** (lines 94-101):
```python
@dataclass
class DatabaseConfig:
    name: str
    base_url: str | None = None
    api_key: str | None = None
    rate_limit: float = 0.3
    batch_size: int = 20
    timeout: int = 30
    retry: RetryConfig | None = None  # NEW — per-provider merged retry config
```

**Need to import RetryConfig:**
```python
from biocurator.config.schema import RetryConfig
```

---

### `src/biocurator/providers/ncbi/searcher.py` (service, CRUD + streaming)

**Analog:** `src/biocurator/providers/ncbi/searcher.py` (existing file)

**Current imports pattern** (lines 1-17):
```python
import time
from pathlib import Path
from typing import Iterator, Any, Callable

from Bio import Entrez, SeqIO

from biocurator.providers.base import (
    DatabaseConfig,
    DatabaseSearcher,
    NCBIDatabase,
    SequenceRecord,
)
from biocurator.providers.ncbi.criteria import NCBISearchCriteria
from biocurator.providers.ncbi.query_builders import get_builder
from biocurator.providers.registry import ProviderRegistry
from biocurator.utils.logging import get_logger
from biocurator.utils.network import retry   # ← REMOVE THIS
```

**NEW imports pattern** (replace `retry` import with tenacity):
```python
from tenacity import (
    retry as tenacity_retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
from biocurator.utils.retryable_exceptions import RETRYABLE_EXCEPTIONS
```

**Current `_safe_entrez_call` pattern** (lines 30-37) — BAD PATTERN to replace:
```python
@retry(exceptions=(Exception,), max_attempts=3)
def _safe_entrez_call(self, func: Callable, **kwargs) -> Any:
    """Execute an Entrez call with retry logic."""
    handle = func(**kwargs)
    try:
        return Entrez.read(handle)
    finally:
        handle.close()
```

**NEW `_safe_entrez_call` pattern** — split parse from network call:
```python
def _safe_entrez_call(self, func: Callable, **kwargs) -> Any:
    """Execute an Entrez HTTP call with retry logic.

    Only the HTTP call (func(**kwargs)) is retried.
    Parse errors from Entrez.read() are NOT retried.
    """
    retryer = Retrying(
        stop=stop_after_attempt(self.config.retry.max_attempts),
        wait=wait_exponential(
            multiplier=self.config.retry.backoff_factor,
            max=self.config.retry.max_delay,
        ),
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        reraise=True,
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    handle = retryer(func, **kwargs)
    # Parse happens OUTSIDE the retry — parse errors fail immediately
    try:
        result = Entrez.read(handle)
        return result
    finally:
        handle.close()
```

**Current `search()` pattern** (lines 42-64) — BAD PATTERN to replace:
```python
def search(self, criteria: NCBISearchCriteria) -> list[str]:
    logger.info(f"Searching NCBI {criteria.database} database...")
    query = self.build_query(criteria)
    logger.info(f"Search query: {query}")
    try:
        results = self._safe_entrez_call(
            Entrez.esearch,
            db=criteria.database,
            term=query,
            retmax=criteria.max_results,
            sort="relevance",
            usehistory="y",
        )
        ids = results.get("IdList", [])
        criteria.webenv = results.get("WebEnv")
        criteria.query_key = results.get("QueryKey")
        logger.info(f"Found {len(ids)} potential sequences (History Server active)")
        return ids
    except Exception as exc:           # ← SILENT SWALLOWING
        logger.error(f"Error searching NCBI: {exc}")
        return []                       # ← RETURNS EMPTY LIST ON FAILURE
```

**NEW `search()` pattern** — raise typed exception:
```python
def search(self, criteria: NCBISearchCriteria) -> list[str]:
    logger.info(f"Searching NCBI {criteria.database} database...")
    query = self.build_query(criteria)
    logger.info(f"Search query: {query}")
    try:
        handle = self._safe_entrez_call(
            Entrez.esearch,
            db=criteria.database,
            term=query,
            retmax=criteria.max_results,
            sort="relevance",
            usehistory="y",
        )
        results = Entrez.read(handle)   # Parse separate from retry
        handle.close()

        ids = results.get("IdList", [])
        criteria.webenv = results.get("WebEnv")
        criteria.query_key = results.get("QueryKey")
        logger.info(f"Found {len(ids)} potential sequences (History Server active)")
        return ids
    except DatabaseSearchError:
        raise  # Already a typed error — let it propagate
    except RETRYABLE_EXCEPTIONS as exc:
        raise DatabaseSearchError(f"NCBI search failed after retries: {exc}") from exc
    except Exception as exc:
        raise DatabaseSearchError(f"NCBI search error: {exc}") from exc
```

**Current `fetch_metadata()` pattern** (lines 66-110) — KEEP the `except Exception` but NARROW it:
```python
# Current catch-all (line 107):
except Exception as exc:
    logger.warning(
        f"Error fetching metadata for batch {i // self.config.batch_size + 1}: {exc}"
    )
# NEW: Keep this pattern but narrow to RETRYABLE_EXCEPTIONS for retryable errors.
# Non-retryable (parse) errors should also be caught and logged as warnings,
# since generators should continue on per-record failure.
# The _safe_entrez_call's tenacity handles retries internally.
```

**Current inline `_fetch()` in download** (lines 142-149) — BAD PATTERN to replace:
```python
@retry(exceptions=(Exception,), max_attempts=3)
def _fetch():
    handle = Entrez.efetch(**params)
    try:
        return SeqIO.read(handle, "fasta")
    finally:
        handle.close()
```

**NEW pattern** — refactor to method-level helper using `Retrying` class:
```python
def _fetch_single(self, params: dict) -> SeqRecord:
    """Fetch a single sequence with retry. Parse outside retry."""
    retryer = Retrying(
        stop=stop_after_attempt(self.config.retry.max_attempts),
        wait=wait_exponential(
            multiplier=self.config.retry.backoff_factor,
            max=self.config.retry.max_delay,
        ),
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        reraise=True,
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    handle = retryer(Entrez.efetch, **params)
    try:
        return SeqIO.read(handle, "fasta")
    finally:
        handle.close()
```

---

### `src/biocurator/providers/uniprot/searcher.py` (service, CRUD + streaming)

**Analog:** `src/biocurator/providers/uniprot/searcher.py` (existing file)

**Current imports pattern** (lines 1-15):
```python
import time
from io import StringIO
from pathlib import Path
from typing import Iterator

from requests import Session

from Bio import SeqIO

from biocurator.providers.base import DatabaseConfig, DatabaseSearcher, SequenceRecord
from biocurator.providers.uniprot.criteria import UniProtSearchCriteria
from biocurator.providers.uniprot.query_builders import UniProtQueryBuilder
from biocurator.providers.registry import ProviderRegistry
from biocurator.utils.logging import get_logger
from biocurator.utils.network import retry   # ← REMOVE THIS
```

**NEW imports pattern:**
```python
from tenacity import (
    retry as tenacity_retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)
from biocurator.utils.retryable_exceptions import RETRYABLE_EXCEPTIONS
```

**Current `_safe_get` pattern** (lines 28-32) — BAD PATTERN to replace:
```python
@retry(exceptions=(Exception,), max_attempts=3)
def _safe_get(self, url: str, **kwargs):
    response = self.session.get(url, **kwargs)
    response.raise_for_status()
    return response
```

**NEW `_safe_get` pattern** — tenacity with exception narrowing (4xx not retried):
```python
def _safe_get(self, url: str, **kwargs):
    """Retry a GET request with configurable tenacity Retrying."""
    retryer = Retrying(
        stop=stop_after_attempt(self.config.retry.max_attempts),
        wait=wait_exponential(
            multiplier=self.config.retry.backoff_factor,
            max=self.config.retry.max_delay,
        ),
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        reraise=True,
        before_sleep=before_sleep_log(logger, logging.WARNING),
    )
    response = retryer(self.session.get, url, **kwargs)
    response.raise_for_status()  # 4xx raises HTTPError here (non-retryable, outside retry)
    return response
```

**Current `search()` pattern** (lines 37-55) — BAD PATTERN to replace:
```python
def search(self, criteria: UniProtSearchCriteria) -> list[str]:
    logger.info("Searching UniProt database...")
    query = self.build_query(criteria)
    try:
        url = f"{self._base_url}/uniprotkb/search"
        params = {
            "query": query,
            "format": "tsv",
            "fields": "accession",
            "size": min(criteria.max_results, 500),
        }
        response = self._safe_get(url, params=params, timeout=self.config.timeout)
        lines = response.text.strip().split("\n")[1:]
        ids = [line.strip() for line in lines if line.strip()]
        logger.info(f"Found {len(ids)} UniProt entries")
        return ids
    except Exception as exc:           # ← SILENT SWALLOWING
        logger.error(f"Error searching UniProt: {exc}")
        return []                       # ← RETURNS EMPTY LIST ON FAILURE
```

**NEW `search()` pattern** — raise typed exception:
```python
def search(self, criteria: UniProtSearchCriteria) -> list[str]:
    logger.info("Searching UniProt database...")
    query = self.build_query(criteria)
    try:
        url = f"{self._base_url}/uniprotkb/search"
        params = {
            "query": query,
            "format": "tsv",
            "fields": "accession",
            "size": min(criteria.max_results, 500),
        }
        response = self._safe_get(url, params=params, timeout=self.config.timeout)
        lines = response.text.strip().split("\n")[1:]
        ids = [line.strip() for line in lines if line.strip()]
        logger.info(f"Found {len(ids)} UniProt entries")
        return ids
    except DatabaseSearchError:
        raise
    except RETRYABLE_EXCEPTIONS as exc:
        raise DatabaseSearchError(f"UniProt search failed: {exc}") from exc
    except Exception as exc:
        raise DatabaseSearchError(f"UniProt search error: {exc}") from exc
```

**Current generator error handling pattern** (lines 87-88, 108-109) — KEEP the collect-and-continue pattern, but ensure non-retryable errors are logged and continued:
```python
# fetch_metadata (line 87-88):
except Exception as exc:
    logger.warning(f"Error fetching UniProt metadata for batch {i // batch_size + 1}: {exc}")

# download (lines 108-109):
except Exception as exc:
    logger.warning(f"Failed to download {uid}: {exc}")
```
The `_safe_get` tenacity handles retries internally. After tenacity exhaustion, the exception propagates to these `except Exception` handlers — keep them as-is (they log warning and continue), since these are generator paths.

---

### `src/biocurator/utils/network.py` (utility, request-response)

**Analog:** `src/biocurator/utils/network.py` (being removed)

**Current pattern** (lines 21-80) — entire file to be removed/gutted:
```python
import time
import functools
import random
from typing import Callable, Type, Tuple, Any
from biocurator.utils.logging import get_logger

logger = get_logger(__name__)

def retry(
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    jitter: bool = True,
) -> Callable:
    """Decorator for retrying a function with exponential backoff."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            ...
```

**Decision:** Gut entirely. The `@retry` decorator is replaced by tenacity at all 3 call sites. The file can be:
- Deleted entirely (cleanest), OR
- Gutted to just an `__all__ = []` with a deprecation comment
Depends on whether `tests/utils/test_network.py` needs updating. Those tests test the old `@retry` — they should be migrated to test tenacity behavior instead.

---

### `src/biocurator/exceptions.py` (utility, CRUD)

**Analog:** `src/biocurator/exceptions.py` (existing file)

**Current pattern** (lines 1-31):
```python
class BiocuratorError(Exception):
    """Base exception for all biocurator errors."""

class ConfigNotFoundError(BiocuratorError):
    """Config file path does not exist."""

class InvalidConfigError(BiocuratorError):
    """YAML is malformed or fails schema validation."""

class JobNotFoundError(BiocuratorError):
    """--jobs references a job name not defined in config."""

class DatabaseSearchError(BiocuratorError):
    """Search API call to a remote database failed."""

class DownloadError(BiocuratorError):
    """Sequence download from a remote database failed."""

class ExportError(BiocuratorError):
    """Writing output files to disk failed."""
```

**New exception types to add** (pattern: single `BiocuratorError` subclass, class docstring):
```python
class DatabaseConnectionError(BiocuratorError):
    """Unrecoverable connection error after retry exhaustion."""

class ParseError(BiocuratorError):
    """Failed to parse API response (XML/JSON/TSV parse error)."""
```

These are optional — `DatabaseSearchError` is already sufficient for search failures (it wraps both network and parse errors). If the decision is to keep it simple, `DatabaseSearchError` alone covers the search path; generators just log warnings.

---

### `pyproject.toml` (config)

**Analog:** `pyproject.toml` (existing file)

**Current dependencies pattern** (lines 30-38):
```toml
dependencies = [
    "biopython>=1.87",
    "numpy>=2.0",
    "pandas>=3.0.3",
    "requests>=2.34.2",
    "rich>=13.0",
    "typer>=0.25.1",
    "pyyaml>=6.0",
]
```

**Add tenacity** (following existing pattern, alphabetically):
```toml
dependencies = [
    "biopython>=1.87",
    "numpy>=2.0",
    "pandas>=3.0.3",
    "requests>=2.34.2",
    "rich>=13.0",
    "tenacity>=9.1,<10.0",   # NEW
    "typer>=0.25.1",
    "pyyaml>=6.0",
]
```

---

## Shared Patterns

### Retryable Exception Classification
**Source:** RESEARCH.md (exception classification tables)
**Apply to:** Both searcher files (`ncbi/searcher.py`, `uniprot/searcher.py`)

Create a shared tuple/constant for retryable exceptions to avoid duplication. Location options:
- `src/biocurator/utils/retryable_exceptions.py` (dedicated file, clean)
- `src/biocurator/exceptions.py` (co-located with exception classes)
- Inline in each searcher (DRY violation — not recommended)

```python
# src/biocurator/utils/retryable_exceptions.py (recommended location)
"""Exception types that are safe to retry (transient network errors)."""

import socket
import urllib.error
import requests

RETRYABLE_EXCEPTIONS = (
    # NCBI via Biopython/Bio.Entrez
    urllib.error.URLError,
    urllib.error.HTTPError,      # Only 5xx — must be filtered at call site
    # UniProt via requests
    requests.ConnectionError,
    requests.Timeout,
    requests.HTTPError,          # Only 5xx — must be filtered at call site
    # Low-level socket errors
    socket.timeout,
    socket.gaierror,
)
```

**NOTE:** `urllib.error.HTTPError` and `requests.HTTPError` with 4xx status codes must NOT be retried. The `retry_if_exception_type` in tenacity catches all instances of the type. To handle 4xx vs 5xx differently, add a custom retry predicate:
```python
def _is_retryable_http_error(exc: BaseException) -> bool:
    """Return True only for 5xx HTTP errors (server fault)."""
    if isinstance(exc, requests.HTTPError):
        return exc.response is not None and exc.response.status_code >= 500
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code >= 500
    return False

# Combined retry predicate: type-based + status-based filtering
RETRYABLE_PREDICATE = (retry_if_exception_type(RETRYABLE_EXCEPTIONS) & _is_retryable_http_error)
```

### Config Merge Strategy Pattern
**Apply to:** `Biocurator._init_database_searchers()` in `core/curator.py`

Priority chain (highest to lowest):
1. `JobConfig.search.retry[db_name]` — per-database override at job level
2. `GlobalConfig.retry` — global defaults
3. tenacity built-in defaults

```python
# Merge pattern: override wins, with None sentinel for "not set"
def _resolve_retry_config(
    global_cfg: RetryConfig | None,
    job_override: RetryConfig | None,
) -> RetryConfig:
    """Merge retry configs, with job override taking precedence."""
    base = global_cfg or RetryConfig.defaults()
    if job_override is None:
        return base
    return RetryConfig(
        max_attempts=job_override.max_attempts if job_override.max_attempts != base.max_attempts else base.max_attempts,
        backoff_factor=job_override.backoff_factor if job_override.backoff_factor != base.backoff_factor else base.backoff_factor,
        max_delay=job_override.max_delay if job_override.max_delay != base.max_delay else base.max_delay,
        timeout=job_override.timeout if job_override.timeout != base.timeout else base.timeout,
    )
```

### Logger Pattern
**Source:** `src/biocurator/utils/logging.py` lines 35-38, `src/biocurator/utils/network.py` line 18
**Apply to:** All files
```python
from biocurator.utils.logging import get_logger

logger = get_logger(__name__)
```

### Module Organization Pattern
**Source:** `src/biocurator/providers/__init__.py`, `src/biocurator/providers/ncbi/__init__.py`
**Apply to:** If a new subpackage is created (e.g., `utils/retryable_exceptions.py`)

```python
__all__ = [
    "RetryConfig",
    "SearchConfig",
    "GlobalConfig",
    ...
]
```
Use sorted `__all__` lists, absolute imports from re-exported modules.

### Test Pattern
**Source:** `tests/utils/test_network.py`, `tests/providers/ncbi/test_searcher.py`, `tests/config/test_schema.py`
**Apply to:** New test files

```python
# Simple unit test pattern (no pytest fixture overuse):
from unittest.mock import MagicMock, patch
import pytest

# Desired test pattern for new tests:
def test_search_raises_on_failure():
    """search() raises DatabaseSearchError instead of returning []."""
    searcher = NCBISearcher(config, "test@example.com")
    with patch.object(searcher, "_safe_entrez_call", side_effect=ConnectionError("fail")):
        with pytest.raises(DatabaseSearchError, match="NCBI search failed"):
            searcher.search(NCBISearchCriteria())

def test_generator_continues_on_error():
    """fetch_metadata logs warning and continues on per-record failure."""
    searcher = NCBISearcher(config, "test@example.com")
    with patch.object(searcher, "_safe_entrez_call", side_effect=ValueError("bad data")):
        results = list(searcher.fetch_metadata(["id1", "id2"], NCBISearchCriteria()))
        assert results == []  # Empty but no exception raised
```

### Make `RetryConfig.from_dict()` Pattern
To parse YAML dicts into `RetryConfig` cleanly:
```python
@dataclass
class RetryConfig:
    max_attempts: int = 3
    backoff_factor: float = 2.0
    max_delay: int = 60
    timeout: int = 30

    @classmethod
    def from_dict(cls, data: dict | None) -> "RetryConfig | None":
        """Parse from a YAML dict, returning None if empty/missing."""
        if not data:
            return None
        return cls(
            max_attempts=data.get("max_attempts", 3),
            backoff_factor=data.get("backoff_factor", 2.0),
            max_delay=data.get("max_delay", 60),
            timeout=data.get("timeout", 30),
        )
```

## No Analog Found

All files have exact existing analogs in the codebase — this is a phase that modifies existing files rather than creating entirely new types of files.

## Metadata

**Analog search scope:** `src/biocurator/` (all subpackages), `tests/`, `pyproject.toml`
**Files scanned:** 15+ source files, 10+ test files
**Pattern extraction date:** 2026-05-25

### Key Patterns Identified
1. **Config dataclass pattern** — `@dataclass` with `field(default_factory=...)` for mutable defaults, `Optional` types with `None` defaults for backward compat
2. **Loader YAML parsing pattern** — `data.get("key")` with defaults, raise `InvalidConfigError` for missing required fields
3. **Exception hierarchy pattern** — `BiocuratorError(Exception)` base, simple subclasses with docstring
4. **Custom `@retry` decorator** — to be fully removed and replaced by tenacity
5. **Searcher `_safe_*` method pattern** — helper methods wrapping API calls with retry, currently with `@retry(exceptions=(Exception,))` replaced by tenacity `Retrying` with `retry_if_exception_type(RETRYABLE_EXCEPTIONS)`
6. **search() error handling** — currently `except Exception: return []`, to become `except RETRYABLE_EXCEPTIONS: raise DatabaseSearchError(...)`
7. **Generator error handling** — currently `except Exception: logger.warning(...)`, keep this pattern but narrow
8. **Searcher `__init__` pattern** — receives `config: DatabaseConfig` and `email: str`, stores as `self.config`, `self.email`
9. **Logging pattern** — `logger = get_logger(__name__)` at module level
10. **Test pattern** — `pytest` with `MagicMock`/`patch`, simple assertion-based tests, fixtures for config/searcher setup
