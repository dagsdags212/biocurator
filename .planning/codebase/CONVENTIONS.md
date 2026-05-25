# Coding Conventions

**Analysis Date:** 2026-05-25

## Project Overview

**Language:** Python 3.13+
**Build:** Hatchling via `uv`
**Package:** `biocurator` (src-layout under `src/biocurator/`)
**Current version:** 0.3.0 (`src/biocurator/__init__.py`)
**Dependency management:** `uv sync` with dev group incl. pytest, pytest-mock

**No linter config detected** (no `.ruff.toml`, no `[tool.ruff]` in `pyproject.toml`, no `.pre-commit-config.yaml`). The `.ruff_cache/` directory exists implying ruff has been run, but no committed configuration.

---

## Naming Patterns

| Category | Convention | Example |
|----------|-----------|---------|
| **Classes** | `PascalCase` | `Biocurator`, `SequenceFilter`, `NCBISearchCriteria` |
| **Functions/methods** | `snake_case` | `run_job`, `filter_by_criteria`, `get_logger` |
| **Variables** | `snake_case` | `filtered_metadata_ids`, `common_kwargs` |
| **Constants** | `UPPER_SNAKE_CASE` | `_BUILDER_MAP`, `_SENSITIVE` |
| **Private methods** | `__dunder_prefix` (name mangling) | `__calculate_quality_score`, `__filter_by_quality` |
| **Protected methods** | `_single_prefix` | `_init_database_searchers`, `_parse`, `_parse_job` |
| **Module-level "private"** | `_single_prefix` | `_SensitiveFilter`, `_BUILDER_MAP`, `_FakeSearcher` |
| **Files/directories** | `snake_case.py` | `query_builders.py`, `test_streaming_curation.py` |
| **Test functions** | `snake_case` | `test_run_job_applies_filter`, `test_retry_eventual_success` |
| **Enum members** | `UPPER_SNAKE_CASE` | `NUCCORE`, `PUBMED`, `GENE` |

---

## Module & Package Organization

**Source layout** — all application code under `src/biocurator/`:

```
src/biocurator/
├── __init__.py          # Version string only
├── cli/                 # Typer CLI entry point, command modules
│   ├── main.py
│   └── commands/
│       ├── init.py
│       ├── run.py
│       └── preview.py
├── config/              # YAML configuration loading and schema
│   ├── loader.py
│   └── schema.py
├── core/                # Core curation pipeline logic
│   ├── curator.py
│   ├── exporter.py
│   └── filters.py
├── exceptions.py        # Custom exception hierarchy
├── providers/           # Database provider implementations
│   ├── base.py          # ABCs, dataclasses, enums
│   ├── registry.py      # ProviderRegistry
│   ├── ncbi/            # NCBI (Entrez) implementation
│   │   ├── criteria.py
│   │   ├── query_builders.py
│   │   └── searcher.py
│   └── uniprot/         # UniProt REST API implementation
│       ├── criteria.py
│       ├── query_builders.py
│       └── searcher.py
└── utils/               # Shared utilities
    ├── logging.py
    └── network.py
```

**Package conventions:**
- Each subpackage has an `__init__.py` that exports public API via `__all__` lists (sorted alphabetically). See `src/biocurator/providers/__init__.py`.
- `__init__.py` uses absolute imports from the re-exported modules.
- Module-level code like `ProviderRegistry.register()` runs at import time in `src/biocurator/providers/ncbi/searcher.py:167` and `src/biocurator/providers/uniprot/searcher.py:112`.

---

## Import Style

**Absolute imports are preferred** (vast majority):

```python
from biocurator.providers import ProviderRegistry, DatabaseConfig, SearchCriteria
from biocurator.providers.ncbi import NCBISearchCriteria
from biocurator.utils.logging import get_logger
```

**Relative imports used only for intra-package references:**

```python
from .filters import SequenceFilter            # Within same package (core/)
from ..utils.logging import get_logger         # Parent package (core/ → utils/)
```

**Import ordering** (consistent across all files):
1. Standard library (`pathlib.Path`, `typing.*`, `abc`, `dataclasses`, `enum`, `functools`, `time`)
2. Third-party (`pandas`, `Bio`, `requests`, `typer`, `rich`, `yaml`)
3. Application (`biocurator.*`)
4. Module logger (`logger = get_logger(__name__)`)

**Type-checking-only imports** use `TYPE_CHECKING` guard:

```python
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from biocurator.providers.base import DatabaseConfig, DatabaseSearcher
```

Found in `src/biocurator/providers/registry.py`.

---

## Type Annotations

**Full type annotations throughout.** All functions and methods have annotated parameters and return types.

**New-style union syntax** (Python 3.10+) used consistently, enabled by `requires-python = ">=3.13"`:

```python
# Union — new syntax
def load(path: str | Path) -> GlobalConfig: ...
organism: str | None = None

# Optional — explicit None union
def __init__(self, email: str, outdir: Optional[str] = None) -> None: ...
# Mix of old and new Optional style throughout.
```

**Precise generics:**

```python
class QueryBuilder(ABC, Generic[T]):
    @abstractmethod
    def build(self, criteria: T) -> str: ...

class DatabaseSearcher(ABC, Generic[C]):
    def search(self, criteria: C) -> list[str]: ...
    def fetch_metadata(self, ids: list[str], criteria: C | None = None) -> Iterator[SequenceRecord]: ...
```

**Type aliases** via `TypeVar`:

```python
T = TypeVar("T", bound="SearchCriteria")
C = TypeVar("C", bound="SearchCriteria")
```

**Annotated type** used with Typer options:

```python
debug: Annotated[bool, typer.Option("--debug", help="...")] = False
```

---

## Docstring Style

**Google-style docstrings** — used throughout the codebase.

```python
def load(path: str | Path) -> GlobalConfig:
    """Brief one-line description.

    Parameters
    ----------
    path : str | Path
        Path to config file.

    Returns
    -------
    GlobalConfig
        Parsed configuration object.

    Raises
    ------
    ConfigNotFoundError
        File doesn't exist.
    InvalidConfigError
        YAML malformed or validation failure.
    """
```

**Module-level docstrings** used in 5 files using underline-style headers:

```python
"""
Biocurator Module
====================

This module contains the main Biocurator class that coordinates
sequence search, download, filtering, and organization.


© Jan Emmanuel Samson (2026-)
"""
```

**Short docstrings** for simple functions/classes:

```python
class BiocuratorError(Exception):
    """Base exception for all biocurator errors."""

class SequenceFilter:
    """Helper class for filtering sequence sets based on custom criteria"""
```

---

## Error Handling

**Custom exception hierarchy** in `src/biocurator/exceptions.py`:

```
BiocuratorError (base)
├── ConfigNotFoundError
├── InvalidConfigError
├── JobNotFoundError
├── DatabaseSearchError
├── DownloadError
└── ExportError
```

**Patterns used:**
- **Raise specific exceptions:** `raise ConfigNotFoundError(f"Config file not found: {path}")`
- **Chain exceptions:** `raise InvalidConfigError(f"Invalid YAML: {exc}") from exc`
- **Catch and re-raise as CLI exit:** `typer.Exit(1)` with console error printing
- **Catch and log (non-fatal):** API failures in searchers catch `Exception`, log warning/error, return `[]` or continue
- **Closest to resource:** `StreamingExporter.__exit__` calls `self.close()`
- **Retry decoration:** `@retry(exceptions=(Exception,), max_attempts=3)` for network calls

**Pattern to avoid:** Some catch-blocks use bare `except Exception` (in searchers), which is acceptable for resilient network code but swallows errors silently.

---

## Logging

**Module-level logger pattern** — every module creates a logger:

```python
from biocurator.utils.logging import get_logger
logger = get_logger(__name__)
```

`get_logger()` normalizes names to `biocurator.<module>` format (defined in `src/biocurator/utils/logging.py`).

**Log levels used:**
- `logger.debug(...)` — detailed tracing (quality filter steps, timing, download progress)
- `logger.info(...)` — lifecycle events (initialization complete, found N sequences, filtering complete)
- `logger.warning(...)` — recoverable errors (batch fetch failed, download failed for single record)
- `logger.error(...)` — non-recoverable errors (search failed, max retries exceeded)

**Decorator for function call logging** — `@log_function_call` wraps with timing:

```python
@log_function_call
def my_func():
    ...
```

**Custom logging features:**
- `_SensitiveFilter` — redacts passwords/tokens/keys/secrets from log output
- `PerformanceLogger` — start/end timer for operation duration tracking
- `enable_verbose_logging(console=console)` — attaches RichHandler or StreamHandler

---

## Function Design

**Static methods** used heavily in `SequenceFilter` class — 7 static methods, 0 instance methods.

**Context managers** via `__enter__`/`__exit__` — `StreamingExporter` manages file lifecycle.

**Generator pattern** for streaming — fetch_metadata and download return `Iterator[SequenceRecord]`:

```python
def fetch_metadata(self, ids: list[str], ...) -> Iterator[SequenceRecord]:
    for i in range(0, count, batch_size):
        ...
        yield SequenceRecord(...)
```

**Return types:**
- `list[str]` for searches (IDs)
- `Iterator[SequenceRecord]` for streaming operations
- `dict[str, Path]` from export reporting
- `None` for void methods (`open()`, `close()`)

---

## Data Modeling

**`@dataclass`** for all structured data — 6 dataclasses:

| Class | File | Key Fields |
|-------|------|------------|
| `SearchCriteria` | `providers/base.py` | organism, keywords, min/max_length, date range |
| `NCBISearchCriteria` | `providers/ncbi/criteria.py` | database, taxonomy_filter, location |
| `UniProtSearchCriteria` | `providers/uniprot/criteria.py` | reviewed |
| `DatabaseConfig` | `providers/base.py` | name, base_url, api_key, rate_limit |
| `SequenceRecord` | `providers/base.py` | id, accession, database, title, sequence |
| `SearchConfig` | `config/schema.py` | databases, organism, keywords, max_results |
| `FilterConfig` | `config/schema.py` | min/max_length, quality_threshold |
| `ExportConfig` | `config/schema.py` | outdir, formats, prefix |
| `JobConfig` | `config/schema.py` | name, search, filter, export |
| `GlobalConfig` | `config/schema.py` | email, jobs |

**Immutable data** via `field(default_factory=list)` for mutable defaults.

**Enum** for database constants — `NCBIDatabase(str, Enum)` with 65 members.

**`SequenceRecord`** — primary data transfer object with 15 fields.

---

## Comment Conventions

- **Inline comments** explain non-obvious design decisions (e.g., why organism filter is deferred for NCBI)
- **Comment markers:** `# Note:` for important caveats
- **No TODO/FIXME/HACK markers** found in source code
- **Type ignore comments** used where needed: `# type: ignore[abstract]`, `# type: ignore[attr-defined]`

---

## Commit Message Conventions

Conventional Commits format with `type: description`:

| Type | Examples |
|------|----------|
| `feat:` | `feat: add NCBI QueryBuilder implementations and factory` |
| `fix:` | `fix: make DatabaseSearcher generic, fix curator criteria construction` |
| `refactor:` | `refactor: reorganize tests to mirror provider subpackage structure` |
| `test:` | `test: add tests for streaming curation and retry logic` |
| `docs:` | `docs: update README, wiki, and CHANGELOG for v0.2.0` |
| `build:` | `build: add make build/install commands` |
| `chore:` | `chore: bump version to 0.3.0` |

Subjects are imperative mood, concise (under 72 chars).

---

*Convention analysis: 2026-05-25*
