<!-- generated-by: gsd-doc-writer -->
# Architecture

This document describes the internal design of Biocurator: a config-driven CLI tool for curating biological sequence datasets from NCBI and UniProt.

---

## System Overview

Biocurator is a local command-line application with no server component. A user provides a YAML configuration file that defines one or more curation jobs. Each job specifies which databases to query, what criteria to apply, how to filter results by length or quality, and what output formats to produce.

**Core design goals:**

- **Reliability across unreliable networks** — all external API calls go through exponential-backoff retry and a per-provider circuit breaker that trips after repeated failures, preventing wasted requests against unavailable services.
- **Memory efficiency at scale** — data flows from search through filter through download through export as a streaming `Iterator[SequenceRecord]` pipeline. No intermediate list holds the full result set.
- **Provider extensibility** — concrete searchers for NCBI and UniProt are registered at import time via a static `ProviderRegistry`. Adding a new database provider requires implementing one abstract class and calling `ProviderRegistry.register()`.

---

## Layer Architecture

The codebase is organized into six layers. Each layer depends only on layers below it — no layer imports from one above it.

```
┌──────────────────────────────────────────────┐
│               CLI Layer                      │
│   cli/main.py · cli/commands/                │
│   Typer app, subcommand routing, Rich output │
└────────────────────┬─────────────────────────┘
                     │
┌────────────────────▼─────────────────────────┐
│              Config Layer                    │
│   config/schema.py · config/loader.py        │
│   YAML → typed dataclass graph               │
└────────────────────┬─────────────────────────┘
                     │
┌────────────────────▼─────────────────────────┐
│               Core Layer                     │
│   core/curator.py · core/filters.py          │
│   core/exporter.py · core/verifier.py        │
│   Pipeline orchestration                     │
└────────────────────┬─────────────────────────┘
                     │
┌────────────────────▼─────────────────────────┐
│             Provider Layer                   │
│   providers/base.py · providers/registry.py  │
│   providers/health.py                        │
│   providers/ncbi/ · providers/uniprot/       │
│   Database-specific search and download      │
└────────────────────┬─────────────────────────┘
                     │
┌────────────────────▼─────────────────────────┐
│              Utility Layer                   │
│   utils/logging.py                           │
│   utils/retryable_exceptions.py              │
└────────────────────┬─────────────────────────┘
                     │
┌────────────────────▼─────────────────────────┐
│             Exception Layer                  │
│   exceptions.py                              │
└──────────────────────────────────────────────┘
```

### CLI Layer — `src/biocurator/cli/`

Defines the `biocurator` entry point using Typer. `main.py` registers six subcommands:

| Command | Module | Purpose |
|---------|--------|---------|
| `init` | `commands/init.py` | Scaffold a starter `biocurator_config.yaml` |
| `run` | `commands/run.py` | Execute one or more curation jobs end-to-end |
| `preview` | `commands/preview.py` | Search and display metadata without downloading |
| `status` | `commands/status.py` | Probe provider health and circuit breaker state |
| `jobs` | `commands/jobs.py` | List all jobs defined in the config |
| `files` | `commands/files.py` | List downloaded output files; verify SHA-256 checksums |

The CLI layer catches known exceptions (`ConfigNotFoundError`, `InvalidConfigError`, `JobNotFoundError`) and prints styled error output via Rich before calling `raise typer.Exit(1)`.

### Config Layer — `src/biocurator/config/`

`ConfigLoader.load(path)` reads a YAML file and returns a fully typed `GlobalConfig` dataclass tree. Validation happens in `_parse()` and `_parse_job()`. The loader handles the two-level retry/breaker merge: global values defined at top level, per-database overrides nested under `search.retry` / `search.breaker`.

**Config dataclass hierarchy:**

```
GlobalConfig
├── email: str
├── retry: RetryConfig | None          (global retry defaults)
├── breaker: BreakerConfig | None      (global circuit breaker defaults)
└── jobs: list[JobConfig]
    └── JobConfig
        ├── name: str
        ├── search: SearchConfig
        │   ├── databases: list[str]
        │   ├── organism, sequence_type, keywords, max_results
        │   ├── date_range, exclude_terms, location, taxonomy_filter
        │   ├── retry: dict[str, RetryConfig] | None  (per-db overrides)
        │   └── breaker: dict[str, BreakerConfig] | None
        ├── filter: FilterConfig
        │   ├── min_length, max_length, quality_threshold
        │   └── exclude_terms: list[str]
        └── export: ExportConfig
            ├── outdir, prefix
            └── formats: list[str]  (fasta, csv, json)
```

### Core Layer — `src/biocurator/core/`

**`Biocurator`** (`curator.py`) is the pipeline orchestrator. `run_job(job_config)` executes the full search → filter → download → export sequence. It accepts an optional `progress_callback(phase, current, total)` for non-invasive progress reporting. It also exposes `get_health_status()` which delegates to `HealthChecker` for the `status` command.

**`SequenceFilter`** (`filters.py`) implements the filter phase. `filter_by_criteria()` consumes the stream of `SequenceRecord` objects and yields only those passing length, quality, and exclude-term constraints.

**`StreamingExporter`** (`exporter.py`) is a context manager. It opens output file handles on `__enter__`. On `__exit__` it finalizes JSON arrays, closes file handles, writes a `manifest.json` and `manifest-sha256.txt`, and logs results.

**`FileVerifier`** / **`manifest_verify`** (`verifier.py`) validates previously exported files by re-reading them and comparing SHA-256 hashes against the stored manifest.

### Provider Layer — `src/biocurator/providers/`

Defines the abstract contract and concrete implementations for database access. See [Provider Architecture](#provider-architecture) for detail.

**`ProviderHealthChecker`** / **`HealthChecker`** (`providers/health.py`) runs lightweight connectivity probes against NCBI (via `Bio.Entrez.esearch`) and UniProt (via `requests.get`) and returns a `HealthStatus` dataclass with `reachable`, `response_time_ms`, and `error` fields.

### Utility Layer — `src/biocurator/utils/`

**`utils/logging.py`** provides:
- `get_logger(name)` — returns a `logging.Logger` with `_SensitiveFilter` that redacts passwords, tokens, keys, and secrets.
- `PerformanceLogger` — context manager that records elapsed time for an operation.
- `log_function_call` — decorator that logs function entry/exit at DEBUG level.
- `enable_verbose_logging()` — attaches a Rich handler for styled terminal output.

**`utils/retryable_exceptions.py`** defines exception types treated as transient by the `@retry` decorator.

### Exception Layer — `src/biocurator/exceptions.py`

```
BiocuratorError
├── ConfigNotFoundError   — YAML file path does not exist
├── InvalidConfigError    — YAML malformed or missing required field
├── JobNotFoundError      — --jobs references unknown job name
├── DatabaseSearchError   — provider search failed after retries
├── DownloadError         — sequence download failed after retries
└── ExportError           — file write or format conversion failed
```

---

## Key Abstractions

### `SearchCriteria` — `providers/base.py`

Base dataclass for all search parameters. Shared fields: `organism`, `keywords`, `min_length`, `max_length`, `start_date`, `end_date`, `max_results`, `exclude_terms`, `quality_threshold`.

Provider-specific subclasses:
- **`NCBISearchCriteria`** — adds `database` (`NCBIDatabase` enum), `taxonomy_filter`, `location`.
- **`UniProtSearchCriteria`** — adds `reviewed` (Swiss-Prot filter).

### `SequenceRecord` — `providers/base.py`

The universal data transfer object across the entire pipeline. All providers produce `SequenceRecord` instances; filters and exporters consume them without knowing which database they came from. Key fields: `id`, `accession`, `database`, `title`, `organism`, `sequence_length`, `sequence`, `quality_score`, `create_date`, `update_date`, `taxonomy_id`.

### `DatabaseSearcher[C]` — `providers/base.py`

Generic abstract base class parameterized by criteria type `C`. All provider implementations must fulfill this contract:

| Method | Return | Description |
|--------|--------|-------------|
| `build_query(criteria)` | `str` | Provider-specific query string |
| `search(criteria)` | `list[str]` | Returns matching record IDs |
| `fetch_metadata(ids, criteria)` | `Iterator[SequenceRecord]` | Lightweight metadata records |
| `download(ids, outdir, criteria)` | `Iterator[SequenceRecord]` | Full records with sequence data |

### `QueryBuilder[T]` — `providers/base.py`

Generic strategy interface for query string construction. Implementations vary the query syntax per database type while the searcher remains unchanged.

NCBI implementations (in `providers/ncbi/query_builders.py`):

| Class | Database(s) |
|-------|-------------|
| `SequenceQueryBuilder` | `nuccore`, `protein` |
| `LiteratureQueryBuilder` | `pubmed`, `pmc` |
| `GeneQueryBuilder` | `gene` |
| `SRAQueryBuilder` | `sra` |
| `TaxonomyQueryBuilder` | `taxonomy` |

UniProt: `UniProtQueryBuilder` in `providers/uniprot/query_builders.py`.

Factory: `get_builder(db: NCBIDatabase)` in `query_builders.py` resolves the correct builder via `_BUILDER_MAP` at runtime.

### `RetryConfig` / `BreakerConfig` — `config/schema.py`

Both are dataclasses with a `resolve(defaults)` method that merges per-job values with global defaults and falls back to built-in defaults. The merge priority is: **per-database override > global > built-in default**.

`RetryConfig` defaults: max_attempts=3, backoff_factor=2.0, max_delay=60s, timeout=30s.

`BreakerConfig` defaults: fail_max=5, recovery_timeout=60s, half_open_max_successes=1.

---

## Data Flow

### Full Job Execution (`biocurator run`)

```
biocurator run --config biocurator_config.yaml
         │
         ▼
CLI: commands/run.py
ConfigLoader.load(path) → GlobalConfig
Biocurator(email, global_retry, global_breaker) created
_init_database_searchers():
  ProviderRegistry.get("ncbi", ncbi_cfg, email) → NCBISearcher
  ProviderRegistry.get("uniprot", uniprot_cfg, email) → UniProtSearcher
         │
         ▼
Biocurator.run_job(job_config)
         │
   StreamingExporter opened (context manager)
         │
   For each database in job.search.databases:
     1. Merge retry/breaker: per-db > global > defaults
        searcher.config.retry = merged RetryConfig
        searcher._breaker = searcher._init_breaker()
     2. Build criteria: NCBISearchCriteria / UniProtSearchCriteria
     3. ids = searcher.search(criteria)
        └── circuit breaker check → @retry wraps API call
     4. for record in searcher.fetch_metadata(ids, criteria):
           if SequenceFilter.filter_by_criteria([record], criteria):
             filtered_ids.append(record.id)
     5. for seq in searcher.download(filtered_ids, outdir, criteria):
           if quality_filter passes:
             exporter.write_record(seq)
         │
   StreamingExporter.__exit__:
     finalize JSON arrays, close file handles
     write manifest.json + manifest-sha256.txt
         │
         ▼
dict[str, Path] of output files returned
CLI renders summary via Rich
```

### Preview Flow (`biocurator preview`)

Same config loading and `Biocurator` init as `run`. For each database: `search()` + `fetch_metadata()` only (max 10 results per page). No download, no filter, no export. Renders a Rich table: accession | title | organism | length.

### Status Flow (`biocurator status`)

```
biocurator status
  → ConfigLoader.load()
  → Biocurator(email, global_retry, global_breaker)
  → curator.get_health_status()
      HealthChecker.ping_ncbi()    → Bio.Entrez.esearch probe
      HealthChecker.ping_uniprot() → requests.get probe
  → Rich table: Provider | Status | Response Time | Breaker State
```

### Files / Verify Flow (`biocurator files [job] [--verify]`)

Without `--verify`: reads `manifest.json` from each job's `outdir` and renders a file list with size, record count, and SHA-256 prefix.

With `--verify`: calls `manifest_verify(manifest_path)` from `core/verifier.py`, re-reads each file, recomputes SHA-256, and compares against stored hashes. Reports per-file OK / corrupted / missing.

---

## Provider Architecture

```
providers/base.py
  DatabaseSearcher[C]   ABC — contract for all providers
  QueryBuilder[T]        ABC — query string strategy
  SearchCriteria         base dataclass
  SequenceRecord         universal DTO
  DatabaseConfig         connection parameters
  NCBIDatabase           Enum (NUCCORE, PROTEIN, PUBMED, GENE, SRA, TAXONOMY, ...)

providers/registry.py
  ProviderRegistry       static dict: name → searcher class
                         populated at import time via .register()

providers/health.py
  HealthStatus           dataclass (provider, reachable, response_time_ms, error)
  HealthChecker          static methods: ping_ncbi(), ping_uniprot()

providers/ncbi/
  NCBISearchCriteria     extends SearchCriteria (+database, taxonomy_filter, location)
  NCBISearcher           implements DatabaseSearcher[NCBISearchCriteria]
    uses:  Bio.Entrez (esearch, efetch)
    holds: _breaker (CircuitBreaker via pybreaker)
    self-registers: ProviderRegistry.register("ncbi", NCBISearcher)
  query_builders.py      five QueryBuilder implementations + get_builder factory
  circuit_breaker.py     NCBICircuitBreaker wrapper

providers/uniprot/
  UniProtSearchCriteria  extends SearchCriteria (+reviewed bool)
  UniProtSearcher        implements DatabaseSearcher[UniProtSearchCriteria]
    uses:  requests → rest.uniprot.org/uniprotkb
    holds: _breaker (CircuitBreaker via pybreaker)
    self-registers: ProviderRegistry.register("uniprot", UniProtSearcher)
  query_builders.py      UniProtQueryBuilder
  circuit_breaker.py     UniProtCircuitBreaker wrapper
```

**Registration at import time:** Both `NCBISearcher` and `UniProtSearcher` call `ProviderRegistry.register()` at module level. The registration happens automatically when the module is first imported — no explicit setup is required by the caller. `Biocurator._init_database_searchers()` triggers the import by calling `ProviderRegistry.get(name, cfg, email)`.

---

## Design Patterns

| Pattern | Location | Usage |
|---------|----------|-------|
| **Strategy** | `QueryBuilder[T]` implementations | Encapsulates query-string construction per database type; selected at runtime via `get_builder()` |
| **Factory** | `get_builder(db)` | Returns correct `QueryBuilder` via `_BUILDER_MAP` without the caller knowing the concrete type |
| **Registry** | `ProviderRegistry` | Maps provider name strings to searcher classes; populated via `register()` at import time |
| **Template Method** | `DatabaseSearcher[C]` ABC | Defines `search → fetch_metadata → download` skeleton; subclasses fill in HTTP/Entrez details |
| **Abstract Factory** | `Biocurator._init_database_searchers()` | Creates concrete searcher instances from config via registry |
| **Context Manager** | `StreamingExporter` | `__enter__` opens file handles; `__exit__` finalizes JSON, writes manifest, closes handles |
| **Generator / Iterator** | All `fetch_metadata()` and `download()` methods | Lazy streaming via `yield` keeps memory bounded regardless of result set size |
| **Decorator** | `@retry`, `@log_function_call` | Separates retry and logging concerns from business logic |
| **Circuit Breaker** | `NCBICircuitBreaker`, `UniProtCircuitBreaker` | Trips after `fail_max` consecutive failures; prevents wasted calls to unavailable services |
| **Null Object / Defaults** | Config dataclasses with `None` defaults | Optional fields degrade gracefully; `RetryConfig.resolve()` / `BreakerConfig.resolve()` fill in built-in defaults |
| **Callback** | `progress_callback` in `run_job()` | Decouples pipeline progress events from the UI layer |

---

## Circuit Breaker State Machine

```
CLOSED ──(fail_max consecutive failures)──► OPEN
  ▲                                           │
  │                                           │ recovery_timeout elapses
  │                                           ▼
  └────(half_open_max_successes probes)── HALF-OPEN
                                              │
                                       (probe fails)
                                              ▼
                                           OPEN (reset timer)
```

In **OPEN** state, calls fail immediately without a network request. In **HALF-OPEN** state, a limited number of probe requests are allowed through. A successful probe closes the circuit; a failed probe reopens it.

Run `biocurator status` to inspect the current state of each provider's circuit breaker.

---

## Module Dependency Graph

```
cli/main.py
    ├── cli/commands/run.py      → core/curator.py → providers/* → utils/*
    ├── cli/commands/preview.py  → providers/*
    ├── cli/commands/status.py   → core/curator.py → providers/health.py
    ├── cli/commands/jobs.py     → config/loader.py
    └── cli/commands/files.py    → config/loader.py → core/verifier.py

core/curator.py
    ├── config/schema.py         (RetryConfig, BreakerConfig, JobConfig)
    ├── core/filters.py
    ├── core/exporter.py
    ├── providers/registry.py
    ├── providers/health.py
    └── utils/logging.py

providers/ncbi/searcher.py
    ├── providers/base.py
    ├── providers/ncbi/criteria.py
    ├── providers/ncbi/query_builders.py
    ├── providers/ncbi/circuit_breaker.py
    └── utils/logging.py

providers/uniprot/searcher.py
    ├── providers/base.py
    ├── providers/uniprot/criteria.py
    ├── providers/uniprot/query_builders.py
    ├── providers/uniprot/circuit_breaker.py
    └── utils/logging.py

config/loader.py
    ├── config/schema.py
    └── exceptions.py
```

---

## Error Handling Strategy

| Failure class | Mechanism | Outcome |
|---------------|-----------|---------|
| Config not found | `ConfigNotFoundError` raised immediately | CLI prints error, exits 1 |
| Config invalid | `InvalidConfigError` raised immediately | CLI prints field/reason, exits 1 |
| Transient network | `@retry` with exponential backoff (default 3 attempts) | Retried transparently; `DatabaseSearchError` raised after exhaustion |
| Provider repeated failure | Circuit breaker trips after `fail_max` | Subsequent calls fail fast with `DatabaseSearchError` until `recovery_timeout` elapses |
| Single record download | Logged as warning, record skipped | Job continues with successfully downloaded subset |
| Export write failure | `ExportError` raised | `StreamingExporter.__exit__` still finalizes partial output |

---

## Directory Structure

```
src/biocurator/
├── __init__.py
├── exceptions.py
├── cli/
│   ├── main.py                    # Typer app + subcommand registration
│   └── commands/
│       ├── init.py                # biocurator init
│       ├── run.py                 # biocurator run
│       ├── preview.py             # biocurator preview
│       ├── status.py              # biocurator status
│       ├── jobs.py                # biocurator jobs
│       └── files.py               # biocurator files
├── config/
│   ├── schema.py                  # RetryConfig, BreakerConfig, SearchConfig, ...
│   └── loader.py                  # ConfigLoader
├── core/
│   ├── curator.py                 # Biocurator — pipeline orchestrator
│   ├── filters.py                 # SequenceFilter
│   ├── exporter.py                # StreamingExporter (context manager)
│   └── verifier.py                # manifest_verify, FileVerifier
├── providers/
│   ├── base.py                    # ABCs + core dataclasses
│   ├── registry.py                # ProviderRegistry
│   ├── health.py                  # HealthChecker, HealthStatus
│   ├── ncbi/
│   │   ├── criteria.py            # NCBISearchCriteria, NCBIDatabase enum
│   │   ├── searcher.py            # NCBISearcher
│   │   ├── query_builders.py      # 5 QueryBuilder impls + get_builder
│   │   └── circuit_breaker.py     # NCBICircuitBreaker
│   └── uniprot/
│       ├── criteria.py            # UniProtSearchCriteria
│       ├── searcher.py            # UniProtSearcher
│       ├── query_builders.py      # UniProtQueryBuilder
│       └── circuit_breaker.py     # UniProtCircuitBreaker
└── utils/
    ├── logging.py                 # get_logger, PerformanceLogger, _SensitiveFilter
    └── retryable_exceptions.py    # Exception types treated as transient
```
