# Codebase Structure

**Analysis Date:** 2026-05-25

## Directory Layout

```
biocurator/
├── .github/
│   └── workflows/
│       ├── ci.yml               # GitHub Actions: pytest on push/PR
│       └── publish.yml          # GitHub Actions: PyPI publish
├── .planning/
│   └── codebase/                # GSD codebase analysis documents
├── docs/
│   └── plans/                   # Design/implementation plans (7 markdown files)
├── src/
│   └── biocurator/
│       ├── __init__.py           # Package version (0.3.0)
│       ├── exceptions.py         # Exception hierarchy
│       ├── cli/
│       │   ├── main.py           # Typer app definition with 3 commands
│       │   └── commands/
│       │       ├── init.py       # biocurator init — generate starter config
│       │       ├── run.py        # biocurator run — execute curation jobs
│       │       └── preview.py    # biocurator preview — inspect results without download
│       ├── config/
│       │   ├── schema.py         # Dataclass definitions (5 classes)
│       │   └── loader.py         # YAML config loader/parser
│       ├── core/
│       │   ├── curator.py        # Biocurator orchestrator class
│       │   ├── exporter.py       # StreamingExporter (FASTA/CSV/JSON writer)
│       │   └── filters.py        # SequenceFilter (length/quality/organism/date/taxonomy)
│       ├── providers/
│       │   ├── base.py           # ABCs: DatabaseSearcher, QueryBuilder; Value objects: SearchCriteria, SequenceRecord, DatabaseConfig, NCBIDatabase
│       │   ├── registry.py       # ProviderRegistry (static class-level registry)
│       │   ├── ncbi/
│       │   │   ├── criteria.py       # NCBISearchCriteria
│       │   │   ├── query_builders.py # 5 QueryBuilder implementations + get_builder factory
│       │   │   └── searcher.py       # NCBISearcher (Entrez E-utilities)
│       │   └── uniprot/
│       │       ├── criteria.py       # UniProtSearchCriteria
│       │       ├── query_builders.py # UniProtQueryBuilder
│       │       └── searcher.py       # UniProtSearcher (REST API)
│       └── utils/
│           ├── logging.py        # Logger factory, PerformanceLogger, log decorator
│           └── network.py        # Retry decorator with exponential backoff
├── tests/
│   ├── __init__.py
│   ├── test_exceptions.py       # Exception hierarchy tests
│   ├── fixtures/
│   │   ├── valid_config.yaml
│   │   ├── missing_email.yaml
│   │   └── missing_databases.yaml
│   ├── cli/
│   │   ├── test_init.py
│   │   └── test_run.py
│   ├── config/
│   │   ├── test_schema.py
│   │   └── test_loader.py
│   ├── core/
│   │   ├── test_curator.py
│   │   └── test_streaming_curation.py
│   ├── providers/
│   │   ├── test_base.py
│   │   ├── test_registry.py
│   │   ├── test_sequence_record.py
│   │   ├── ncbi/
│   │   │   ├── test_apikey.py
│   │   │   ├── test_criteria.py
│   │   │   ├── test_query_builders.py
│   │   │   └── test_searcher.py
│   │   └── uniprot/
│   │       ├── test_criteria.py
│   │       ├── test_query_builders.py
│   │       └── test_searcher.py
│   └── utils/
│       ├── test_logging.py
│       └── test_network.py
├── wiki/                        # 11 GitHub wiki markdown pages
├── docs/
│   └── plans/                   # 7 design/implementation plan documents
├── main.py                      # Programmatic API example (standalone)
├── config.yaml                  # Default config with 3 jobs (ASFV, COVID, CYP450)
├── pyproject.toml               # Project metadata, dependencies, build config
├── Makefile                     # test/build/install convenience targets
├── README.md                    # Full usage documentation (426 lines)
├── CHANGELOG.md                 # Keep a Changelog format (165 lines)
├── LICENSE                      # MIT
├── uv.lock                      # Lockfile (uv)
└── .python-version              # Python version (3.13)
```

## Directory Purposes

### `src/biocurator/` — Main Package

**Purpose:** All application source code. Split into 5 subpackages + exceptions.

- **`__init__.py`** — Exports `__version__ = "0.3.0"` only. No public API re-exports at package level.
- **`exceptions.py`** — 7 exception classes in a single hierarchy: `BiocuratorError` → 6 subclasses (`ConfigNotFoundError`, `InvalidConfigError`, `JobNotFoundError`, `DatabaseSearchError`, `DownloadError`, `ExportError`)

### `src/biocurator/cli/` — CLI Layer

**Purpose:** Command-line interface built with Typer + Rich. Defines the `biocurator` CLI app.

- **`main.py`** — Creates `typer.Typer` app with 3 commands registered via `app.command()`. Defines shared Rich console and helper functions (`print_success`, `print_error`, `print_warning`, `print_info`). Callback handles `--debug` and `--version` flags.
- **`commands/__init__.py`** — Empty (package marker)
- **`commands/init.py`** — `biocurator init` command. Contains 2 YAML template strings (`BASIC_TEMPLATE`, `ADVANCED_TEMPLATE`). Writes config to file or prints syntax-highlighted YAML to stdout.
- **`commands/run.py`** — `biocurator run` command. Loads config, optionally filters jobs, creates `Biocurator` instance, runs each job with Rich progress bars (custom `ProcessingSpeedColumn`), renders per-job summary table.
- **`commands/preview.py`** — `biocurator preview` command. Loads config, finds job by name, performs search + metadata fetch only (max 10 results per database), renders Rich table with accession/title/organism/length.

### `src/biocurator/config/` — Config Layer

**Purpose:** YAML configuration schema and loader.

- **`schema.py`** — 5 typed dataclasses: `SearchConfig`, `FilterConfig`, `ExportConfig`, `JobConfig`, `GlobalConfig`. All fields have sensible defaults. Used as the typed API for job definitions.
- **`loader.py`** — `ConfigLoader` class with static `load()` method. Reads YAML, converts to `GlobalConfig` via `_parse()` and `_parse_job()`. Validates required fields (`email`, `search.databases`). Raises `ConfigNotFoundError` or `InvalidConfigError`.

### `src/biocurator/core/` — Core Orchestration

**Purpose:** Central curation pipeline logic — search coordination, filtering, and streaming export.

- **`curator.py`** — `Biocurator` class. On init: sets up `DatabaseConfig` for NCBI and UniProt, populates `self.searchers` dict via `ProviderRegistry.get()`. `run_job()` method drives the full pipeline for a single `JobConfig`: iterates databases, constructs criteria objects, calls searcher.search() → fetch_metadata() → filter → download() → StreamingExporter.write_record(). Accepts optional `progress_callback`.
- **`exporter.py`** — `StreamingExporter` context manager. Open file handles for FASTA/CSV/JSON on `__enter__`, writes incrementally per record via `write_record()`, closes handles (with JSON list finalization) on `__exit__`.
- **`filters.py`** — `SequenceFilter` static-method class. Methods: `filter_by_criteria()` (length, organism, exclude terms, quality), `apply_quality_filter()` (N/X content scoring), `remove_duplicates()`, `filter_by_taxonomy()`, `filter_by_date_range()`.

### `src/biocurator/providers/` — Provider Layer

**Purpose:** Abstract interfaces + concrete implementations for database access. Extensible plugin architecture.

- **`base.py`** — Core abstractions:
  - `NCBIDatabase(StrEnum)` — 39 NCBI Entrez database identifiers across 10 categories
  - `SearchCriteria` — Base dataclass for search parameters
  - `QueryBuilder[T](ABC)` — Generic strategy interface: `build()` returns query string, `available_fields()` returns field docs
  - `DatabaseConfig` — Connection config dataclass
  - `SequenceRecord` — Universal data transfer object
  - `DatabaseSearcher[C](ABC)` — Generic abstract searcher with 4 abstract methods
- **`registry.py`** — `ProviderRegistry` with class-level `_registry: dict[str, type[DatabaseSearcher]]`. Methods: `register()`, `get()`, `available()`.
- **`ncbi/`** — NCBI Entrez provider:
  - `criteria.py` — `NCBISearchCriteria(SearchCriteria)` extends with `database`, `taxonomy_filter`, `location`, `webenv`, `query_key`
  - `query_builders.py` — 5 concrete `QueryBuilder` implementations (`SequenceQueryBuilder`, `LiteratureQueryBuilder`, `GeneQueryBuilder`, `SRAQueryBuilder`, `TaxonomyQueryBuilder`), `_BUILDER_MAP` dict mapping `NCBIDatabase → QueryBuilder`, `get_builder()` factory function
  - `searcher.py` — `NCBISearcher(DatabaseSearcher[NCBISearchCriteria])` using `Bio.Entrez`. Uses Entrez history server (`WebEnv`, `QueryKey`), configurable batch size and rate limit, `@retry`-wrapped `_safe_entrez_call()`. Registers itself: `ProviderRegistry.register("ncbi", NCBISearcher)` at module bottom.
- **`uniprot/`** — UniProt REST API provider:
  - `criteria.py` — `UniProtSearchCriteria(SearchCriteria)` extends with `reviewed: bool | None`
  - `query_builders.py` — `UniProtQueryBuilder(QueryBuilder[UniProtSearchCriteria])` — UniProt REST query format
  - `searcher.py` — `UniProtSearcher(DatabaseSearcher[UniProtSearchCriteria])` using `requests.Session`. Calls REST endpoints `/uniprotkb/search` and `/uniprotkb/accessions` for metadata, `/uniprotkb/{uid}.fasta` for sequences. Registers itself: `ProviderRegistry.register("uniprot", UniProtSearcher)` at module bottom.

### `src/biocurator/utils/` — Utilities

**Purpose:** Cross-cutting utility modules shared by all layers.

- **`logging.py`** — `get_logger()` (creates hierarchical `biocurator.*` loggers), `PerformanceLogger` (timer-based), `log_function_call` decorator, `log_config()`, `enable_verbose_logging()` (attaches RichHandler or StreamHandler), `_SensitiveFilter` (redacts sensitive data from logs).
- **`network.py`** — `retry()` decorator factory: configurable exception types, max attempts, initial delay, backoff factor, jitter. Used by both `NCBISearcher` and `UniProtSearcher`.

## Key File Locations

**Entry Points:**
- `src/biocurator/cli/main.py` — Typer app defined as `app`; exposed via `[project.scripts] biocurator = "biocurator.cli.main:app"` in `pyproject.toml`
- `main.py` — Standalone Python API example (root level, not part of the package)
- `config.yaml` — Default YAML config with 3 example jobs

**Configuration:**
- `pyproject.toml` — Project metadata, dependencies, build system (hatchling), CLI entry point
- `Makefile` — `test`, `build`, `install` targets
- `.python-version` — Python 3.13 constraint

**Source Tree (all under `src/biocurator/`):**
- Package root: `__init__.py` (version only)
- CLI: `cli/main.py`, `cli/commands/{init,run,preview}.py`
- Config: `config/schema.py`, `config/loader.py`
- Core: `core/curator.py`, `core/exporter.py`, `core/filters.py`
- Providers: `providers/base.py`, `providers/registry.py`, `providers/ncbi/*.py`, `providers/uniprot/*.py`
- Utils: `utils/logging.py`, `utils/network.py`
- Exceptions: `exceptions.py`

**Testing:**
- Root: `tests/test_exceptions.py`
- Per-module subdirectories: `tests/cli/`, `tests/config/`, `tests/core/`, `tests/providers/`, `tests/utils/`
- Fixtures: `tests/fixtures/` (3 YAML config files)

## Naming Conventions

**Files:**
- Source files: lowercase with underscores (snake_case) — `schema.py`, `query_builders.py`, `test_streaming_curation.py`
- Test files: `test_<module>.py` — co-located in subdirectories mirroring `src/biocurator/` structure

**Directories:**
- All lowercase, short names — `cli`, `config`, `core`, `providers`, `utils`, `tests`
- Provider subdirectories match the database name — `ncbi/`, `uniprot/`
- Commands in `cli/commands/` subdirectory

**Functions/Methods:**
- snake_case: `run_job()`, `fetch_metadata()`, `enable_verbose_logging()`
- Private methods prefixed with `_`: `_init_database_searchers()`, `_parse()`
- Name-mangled: `__filter_by_quality()`, `__calculate_quality_score()`

**Classes:**
- PascalCase: `Biocurator`, `SequenceFilter`, `StreamingExporter`, `NCBISearcher`, `ProviderRegistry`, `SequenceQueryBuilder`

**Constants:**
- UPPER_SNAKE_CASE: `BASIC_TEMPLATE`, `ADVANCED_TEMPLATE`, `_BUILDER_MAP`, `_SENSITIVE`

**Type Variables:**
- Single uppercase: `T`, `C` (in generic ABCs `QueryBuilder[T]`, `DatabaseSearcher[C]`)

## Where to Add New Code

### New Feature (e.g., new CLI command)
- Implementation: `src/biocurator/cli/commands/<command_name>.py`
- Register in: `src/biocurator/cli/main.py` via `app.command()`
- Tests: `tests/cli/test_<command_name>.py`

### New Database Provider
- Package: `src/biocurator/providers/<dbname>/`
  - `criteria.py` — Extend `SearchCriteria` with DB-specific fields
  - `query_builders.py` — Implement `QueryBuilder[T]`
  - `searcher.py` — Implement `DatabaseSearcher[C]`, register via `ProviderRegistry.register()`
- Re-export in: `src/biocurator/providers/__init__.py`
- Tests: `tests/providers/<dbname>/`
  - `test_criteria.py`, `test_query_builders.py`, `test_searcher.py`

### New Core Pipeline Logic (e.g., new export format)
- Implementation: add to `src/biocurator/core/exporter.py` (update `StreamingExporter`) or create new file in `src/biocurator/core/`
- Tests: `tests/core/test_<module>.py`

### New Config Field
- Update: `src/biocurator/config/schema.py` (dataclass field)
- Update: `src/biocurator/config/loader.py` (parsing)
- Update: any `SearchCriteria` subclasses that need to pass the field
- Tests: `tests/config/test_schema.py`, `tests/config/test_loader.py`

### New Utility
- Add to existing file in `src/biocurator/utils/` or create new file
- Tests: `tests/utils/test_<module>.py`

## Test Structure

Tests mirror the source tree structure exactly:

| Source | Tests |
|--------|-------|
| `src/biocurator/exceptions.py` | `tests/test_exceptions.py` |
| `src/biocurator/cli/commands/init.py` | `tests/cli/test_init.py` |
| `src/biocurator/cli/commands/run.py` | `tests/cli/test_run.py` |
| `src/biocurator/config/schema.py` | `tests/config/test_schema.py` |
| `src/biocurator/config/loader.py` | `tests/config/test_loader.py` |
| `src/biocurator/core/curator.py` | `tests/core/test_curator.py`, `tests/core/test_streaming_curation.py` |
| `src/biocurator/providers/base.py` | `tests/providers/test_base.py` |
| `src/biocurator/providers/registry.py` | `tests/providers/test_registry.py` |
| `src/biocurator/providers/ncbi/*.py` | `tests/providers/ncbi/*.py` |
| `src/biocurator/providers/uniprot/*.py` | `tests/providers/uniprot/*.py` |
| `src/biocurator/utils/logging.py` | `tests/utils/test_logging.py` |
| `src/biocurator/utils/network.py` | `tests/utils/test_network.py` |

**Test fixtures:** YAML files in `tests/fixtures/` (3 files: `valid_config.yaml`, `missing_email.yaml`, `missing_databases.yaml`) — loaded by `tests/config/test_loader.py` via `Path(__file__).parent.parent / "fixtures"`.

**Test runner:** pytest (configured via `[dependency-groups] dev` in `pyproject.toml`). CI runs `uv run pytest -v --tb=short`.

## Special Directories

**`.planning/`:**
- Purpose: GSD (Goal-Structured Development) planning artifacts
- Generated: Yes (by GSD commands)
- Committed: Yes

**`wiki/`:**
- Purpose: GitHub wiki content (11 markdown pages covering all documentation topics)
- Generated: No (hand-maintained)
- Committed: Yes

**`docs/plans/`:**
- Purpose: Architectural design and implementation plans from 2026-05-16–18
- Generated: Yes (design docs)
- Committed: Yes

**`dist/`:**
- Purpose: Built distribution packages (wheel + sdist)
- Generated: Yes (by `uv build`)
- Committed: No (in `.gitignore`)

## Monorepo/Workspace

Not a monorepo — single Python package (`biocurator`). The `pyproject.toml` has a `[tool.uv.workspace]` section but only references itself. The project uses `uv` for dependency management, `hatchling` for build, and publishes to PyPI as a single package.

---

*Structure analysis: 2026-05-25*
