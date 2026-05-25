<!-- GSD:project-start source:PROJECT.md -->
## Project

**Biocurator**

A config-driven command-line tool for curating biological sequence datasets from NCBI and UniProt. Users define curation jobs in YAML (search criteria, filters, export formats) and run them via CLI to reliably download and verify FASTA, CSV, or JSON data.

**Core Value:** Reliably download verified biological sequence data from public databases with a single CLI command, even across intermittent network failures.

### Constraints

- **Python**: Must support Python 3.13+ (enforced in pyproject.toml)
- **API compliance**: Must respect NCBI Entrez usage guidelines (rate limits, email identification)
- **Backwards compatibility**: Existing YAML config format must remain valid
- **No external services**: All functionality must work offline except the database API calls themselves
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Python 3.13+ — all application code
- YAML — configuration format for curation job definitions (`config.yaml`)
- Markdown — documentation
## Runtime
- Python 3.13 (enforced via `.python-version` and `requires-python = ">=3.13"` in `pyproject.toml`)
- **uv** (Astral) — fast Python package installer/resolver
- Lockfile: `uv.lock` (487 lines, all resolved versions pinned)
- Build backend: **hatchling** (`pyproject.toml` line 50: `build-backend = "hatchling.build"`)
## Frameworks
- **Typer** `>=0.25.1` (resolved: 0.25.1) — CLI argument parsing and command routing via `biocurator.cli.main:app`
- **Rich** `>=13.0` (resolved: 15.0.0) — terminal output: progress bars, tables, syntax highlighting, styled text
- **pytest** `>=8.0` (resolved: 9.0.3) — test runner
- **pytest-mock** `>=3.0` (resolved: 3.15.1) — mock integration
- **hatchling** — build system and packaging
- **make** — convenience targets (`test`, `build`, `install`) in `Makefile`
- **ruff** — not explicitly in pyproject dependencies but `.ruff_cache/` directory present, indicating it is used (likely installed globally or via pre-commit)
## Key Dependencies
| Package | Version Pin (pyproject) | Resolved (uv.lock) | Purpose |
|---------|------------------------|-------------------|---------|
| `biopython` | `>=1.87` | 1.87 | NCBI Entrez API wrapper (`Bio.Entrez`), FASTA/GenBank parsing (`Bio.SeqIO`) |
| `requests` | `>=2.34.2` | 2.34.2 | HTTP client for UniProt REST API |
| `pandas` | `>=3.0.3` | 3.0.3 | Metadata CSV export, DataFrame construction |
| `numpy` | `>=2.0` | 2.4.4 | Transitive dependency of biopython/pandas, quality score calculations |
| `pyyaml` | `>=6.0` | 6.0.3 | YAML config file parsing (`config.yaml`) |
| `typer` | `>=0.25.1` | 0.25.1 | CLI framework (subcommands: `init`, `run`, `preview`) |
| `rich` | `>=13.0` | 15.0.0 | Terminal UI: progress bars, tables, styled output, syntax highlighting |
| Package | Resolved Version |
|---------|-----------------|
| `click` | 8.3.3 |
| `certifi` | 2026.4.22 |
| `urllib3` | 2.7.0 |
| `charset-normalizer` | 3.4.7 |
| `idna` | 3.15 |
| `colorama` | 0.4.6 |
| `markdown-it-py` | 4.2.0 |
| `mdurl` | 0.1.2 |
| `pygments` | 2.20.0 |
| `shellingham` | 1.5.4 |
| `python-dateutil` | 2.9.0.post0 |
| `tzdata` | 2026.2 |
| `six` | 1.17.0 |
| `iniconfig` | 2.3.0 |
| `packaging` | 26.2 |
| `pluggy` | 1.6.0 |
| `annotated-doc` | 0.0.4 |
## Configuration
- No `.env` files used
- No environment variables required at runtime
- Email for NCBI API access is passed via CLI or YAML config, not env vars
- YAML file (`config.yaml`) loaded at runtime via `ConfigLoader` in `src/biocurator/config/loader.py`
- Config schema defined via dataclasses in `src/biocurator/config/schema.py`:
- `pyproject.toml` — single source of truth for project metadata, dependencies, build config
- No `setup.py`, `setup.cfg`, or `tox.ini`
## Platform Requirements
- Python >= 3.13
- uv (package manager)
- make (optional, for convenience targets)
- No Docker container
- Published to PyPI as `biocurator` package
- CLI entry point: `biocurator` (defined in `[project.scripts]`)
- No server/deployment — runs as a local CLI tool
## CI/CD
- Triggers: push/PR to `main`
- Strategy: Python 3.13 on ubuntu-latest
- Steps:
- Triggers: GitHub Release published
- Two jobs (test -> publish):
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Project Overview
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
## Module & Package Organization
- Each subpackage has an `__init__.py` that exports public API via `__all__` lists (sorted alphabetically). See `src/biocurator/providers/__init__.py`.
- `__init__.py` uses absolute imports from the re-exported modules.
- Module-level code like `ProviderRegistry.register()` runs at import time in `src/biocurator/providers/ncbi/searcher.py:167` and `src/biocurator/providers/uniprot/searcher.py:112`.
## Import Style
## Type Annotations
## Docstring Style
## Error Handling
- **Raise specific exceptions:** `raise ConfigNotFoundError(f"Config file not found: {path}")`
- **Chain exceptions:** `raise InvalidConfigError(f"Invalid YAML: {exc}") from exc`
- **Catch and re-raise as CLI exit:** `typer.Exit(1)` with console error printing
- **Catch and log (non-fatal):** API failures in searchers catch `Exception`, log warning/error, return `[]` or continue
- **Closest to resource:** `StreamingExporter.__exit__` calls `self.close()`
- **Retry decoration:** `@retry(exceptions=(Exception,), max_attempts=3)` for network calls
## Logging
- `logger.debug(...)` — detailed tracing (quality filter steps, timing, download progress)
- `logger.info(...)` — lifecycle events (initialization complete, found N sequences, filtering complete)
- `logger.warning(...)` — recoverable errors (batch fetch failed, download failed for single record)
- `logger.error(...)` — non-recoverable errors (search failed, max retries exceeded)
- `_SensitiveFilter` — redacts passwords/tokens/keys/secrets from log output
- `PerformanceLogger` — start/end timer for operation duration tracking
- `enable_verbose_logging(console=console)` — attaches RichHandler or StreamHandler
## Function Design
- `list[str]` for searches (IDs)
- `Iterator[SequenceRecord]` for streaming operations
- `dict[str, Path]` from export reporting
- `None` for void methods (`open()`, `close()`)
## Data Modeling
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
## Comment Conventions
- **Inline comments** explain non-obvious design decisions (e.g., why organism filter is deferred for NCBI)
- **Comment markers:** `# Note:` for important caveats
- **No TODO/FIXME/HACK markers** found in source code
- **Type ignore comments** used where needed: `# type: ignore[abstract]`, `# type: ignore[attr-defined]`
## Commit Message Conventions
| Type | Examples |
|------|----------|
| `feat:` | `feat: add NCBI QueryBuilder implementations and factory` |
| `fix:` | `fix: make DatabaseSearcher generic, fix curator criteria construction` |
| `refactor:` | `refactor: reorganize tests to mirror provider subpackage structure` |
| `test:` | `test: add tests for streaming curation and retry logic` |
| `docs:` | `docs: update README, wiki, and CHANGELOG for v0.2.0` |
| `build:` | `build: add make build/install commands` |
| `chore:` | `chore: bump version to 0.3.0` |
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Pattern Overview
- **Config-driven pipeline**: YAML config defines one or more jobs, each with search → filter → export phases
- **Streaming pipeline**: Data flows through generators (`Iterator[SequenceRecord]`) to support memory-efficient curation of large datasets
- **Strategy pattern via QueryBuilder**: Per-database query builders implement a common `QueryBuilder[T]` interface with provider-specific logic
- **Abstract Provider pattern**: `DatabaseSearcher` ABC defines the contract for all database providers; concrete implementations handle NCBI Entrez and UniProt REST APIs
- **Registry pattern**: `ProviderRegistry` is a static registry for discovering and instantiating database searcher implementations
- **Exponential backoff retry**: Decorator-based `@retry` wraps all network calls for resilience against transient failures
## Layers
### CLI Layer
- Purpose: User-facing command-line interface using Typer + Rich
- Location: `src/biocurator/cli/`
- Contains: `main.py` (app definition), `commands/` subdirectory with `init.py`, `run.py`, `preview.py`
- Depends on: `config.loader`, `core.curator`, `providers`, `utils.logging`
- Used by: End users via `biocurator` CLI command (entry point in `pyproject.toml`)
### Config Layer
- Purpose: YAML config parsing, validation, and typed dataclass schema
- Location: `src/biocurator/config/`
- Contains: `schema.py` (dataclasses: `SearchConfig`, `FilterConfig`, `ExportConfig`, `JobConfig`, `GlobalConfig`), `loader.py` (`ConfigLoader`)
- Depends on: PyYAML, `exceptions`
- Used by: CLI commands, `core.curator`
### Core Layer
- Purpose: Orchestration of curation pipeline — search, filter, download, export
- Location: `src/biocurator/core/`
- Contains: `curator.py` (`Biocurator`), `filters.py` (`SequenceFilter`), `exporter.py` (`StreamingExporter`)
- Depends on: `providers` (registry, searchers, criteria, base types), `utils.logging`
- Used by: CLI commands
### Provider Layer
- Purpose: Abstract interface + concrete implementations for biological database access
- Location: `src/biocurator/providers/`
- Contains:
- Depends on: `utils.logging`, `utils.network` (retry), Biopython (`Bio.Entrez`, `Bio.SeqIO`), `requests`
- Used by: `core.curator`, CLI `preview` command
### Utility Layer
- Purpose: Shared logging, network retry, and decorator utilities
- Location: `src/biocurator/utils/`
- Contains: `logging.py` (get_logger, PerformanceLogger, log_function_call, enable_verbose_logging), `network.py` (retry decorator with exponential backoff)
- Depends on: Python stdlib only
- Used by: All layers
### Exception Layer
- Purpose: Typed exception hierarchy
- Location: `src/biocurator/exceptions.py`
- Contains: `BiocuratorError` (base), `ConfigNotFoundError`, `InvalidConfigError`, `JobNotFoundError`, `DatabaseSearchError`, `DownloadError`, `ExportError`
- Used by: CLI layer, config layer, core layer
## Data Flow
### Full Job Execution Flow
### Preview Flow
- `biocurator preview <job_name> --config config.yaml`
- Same config loading + Biocurator init as run
- For each database: search + fetch_metadata only (max 10 results)
- Renders Rich Table with accession, title, organism, length
- No filtering or download
## Data Architecture
### Key Abstractions
- Base value object for search parameters
- Fields: `organism`, `keywords`, `min_length`, `max_length`, `start_date`, `end_date`, `max_results`, `exclude_terms`, `quality_threshold`
- Subclassed by:
- Universal data transfer object across all providers
- Fields: `id`, `accession`, `database`, `title`, `organism`, `sequence_length`, `sequence`, `description`, `create_date`, `update_date`, `taxonomy_id`, `authors`, `journal`, `downloaded`, `quality_score`
- Generic abstract searcher parameterized by criteria type `C`
- Methods: `build_query()`, `search()`, `fetch_metadata()`, `download()`
- All methods return/accept `SequenceRecord` for provider-agnostic data exchange
- Generic strategy interface for query string construction
- Methods: `build(criteria: T) -> str`, `available_fields() -> dict[str, str]`
- Implementations: `SequenceQueryBuilder`, `LiteratureQueryBuilder`, `GeneQueryBuilder`, `SRAQueryBuilder`, `TaxonomyQueryBuilder`, `UniProtQueryBuilder`
- Configuration for a database connection
- Fields: `name`, `base_url`, `api_key`, `rate_limit`, `batch_size`, `timeout`
### Provider Architecture
```mermaid
```
### Module Dependency Graph
```mermaid
```
## Configuration Architecture
```
```
- `ConfigLoader.load(path)` — static method, reads YAML, validates, returns `GlobalConfig`
- Side-loaded via `main.py` (programmatic API) or CLI config argument
- `ConfigLoader._parse()` and `_parse_job()` handle nested YAML → typed dataclass conversion
- Missing `email` or `search.databases` raises `InvalidConfigError`
## CLI Command Hierarchy
```
```
## Seacher Initialization Flow
```mermaid
```
- `src/biocurator/providers/ncbi/searcher.py` line 167: `ProviderRegistry.register("ncbi", NCBISearcher)`
- `src/biocurator/providers/uniprot/searcher.py` line 112: `ProviderRegistry.register("uniprot", UniProtSearcher)`
## Design Patterns
| Pattern | Where | Usage |
|---|---|---|
| **Strategy** | `QueryBuilder[T]` implementations | Different query string construction algorithms per database type, selected at runtime via `get_builder()` factory |
| **Factory** | `get_builder(db: NCBIDatabase)` in `providers/ncbi/query_builders.py` | Returns correct `QueryBuilder` for a given NCBI database via `_BUILDER_MAP` lookup |
| **Registry** | `ProviderRegistry` in `providers/registry.py` | Static registry for discovering and instantiating `DatabaseSearcher` implementations by name string |
| **Template Method** | `DatabaseSearcher[C]` ABC | Defines skeleton `search()`, `fetch_metadata()`, `download()` contract; subclasses fill in implementation details |
| **Abstract Factory** | `Biocurator._init_database_searchers()` | Uses `ProviderRegistry.get()` to create concrete searcher instances based on config |
| **Context Manager** | `StreamingExporter` | `__enter__`/`__exit__` for safe file handle lifecycle (open on enter, close with JSON finalization on exit) |
| **Generator/Iterator** | All `fetch_metadata()` and `download()` methods | Streaming memory-efficient data processing via `yield` |
| **Decorator** | `@retry` in `utils/network.py`, `@log_function_call` in `utils/logging.py` | Cross-cutting concerns (retry logic, performance logging) applied via decorators |
| **Null Object / Defaults** | Config dataclasses with `None` defaults | Unset fields gracefully degrade; `SequenceFilter.filter_by_criteria()` handles missing values with conditionals |
| **Callback** | `progress_callback` parameter in `Biocurator.run_job()` | Non-invasive progress reporting decouples pipeline from UI |
## Error Handling
- `BiocuratorError` base class for all project exceptions (`src/biocurator/exceptions.py`)
- Specific subtypes: `ConfigNotFoundError`, `InvalidConfigError`, `JobNotFoundError`, `DatabaseSearchError`, `DownloadError`, `ExportError`
- CLI catches known exceptions (`ConfigNotFoundError`, `InvalidConfigError`) and reports via Rich console with red styling
- `JobNotFoundError` is raised when `--jobs` references unknown job names
- Network-level errors are handled by the `@retry` decorator (exponential backoff, configurable attempts/delay/jitter)
- Per-record download failures are logged as warnings and **skipped** — individual failures don't stop the batch
- `InvalidConfigError` contains descriptive messages about what field/format is wrong
## Streaming Architecture
## Cross-Cutting Concerns
## Adding a New Provider
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
