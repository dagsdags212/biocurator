# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `NCBIDatabase` StrEnum in `biocurator.providers.base` — 39 Entrez database identifiers
  grouped by category (literature, nucleotide, protein, gene, taxonomy, …). Values are valid
  `db=` strings accepted by all Entrez endpoints.
- `QueryBuilder[T]` abstract base class — generic strategy interface with two abstract
  methods: `build(criteria: T) -> str` (produces the database query string) and
  `available_fields() -> dict[str, str]` (enumerates every supported search field with a
  human-readable description).
- Five NCBI `QueryBuilder` implementations in `biocurator.providers.ncbi.query_builders`,
  each tailored to a group of NCBI databases:
  - `SequenceQueryBuilder` — nuccore, nucleotide, protein, IPG; uses `[Organism]`,
    `[Sequence Length]`, `[Publication Date]` tags.
  - `LiteratureQueryBuilder` — PubMed, PMC; uses `[MeSH Terms]`, `[Title/Abstract]`,
    `[Date - Publication]`.
  - `GeneQueryBuilder` — Gene database; uses `[Gene/Protein Name]`, `[Modification Date]`.
  - `SRAQueryBuilder` — SRA; uses `[All Fields]`, `[Platform]`, `[Strategy]`.
  - `TaxonomyQueryBuilder` — Taxonomy; uses `[Scientific Name]`, `[Common Name]`.
- `get_builder(db: NCBIDatabase) -> QueryBuilder[NCBISearchCriteria]` factory in
  `biocurator.providers.ncbi.query_builders` — returns the correct builder for a given
  database; raises `ValueError` for unmapped databases.
- `UniProtQueryBuilder` in `biocurator.providers.uniprot.query_builders` — builds UniProt
  REST query strings with `organism:`, `length:`, `reviewed:` field syntax.
- `NCBISearchCriteria(SearchCriteria)` in `biocurator.providers.ncbi.criteria` — extends
  the base with `database: NCBIDatabase` (default `NUCCORE`), `taxonomy_filter`, and
  `location` fields.
- `UniProtSearchCriteria(SearchCriteria)` in `biocurator.providers.uniprot.criteria` —
  extends the base with `reviewed: bool | None` for Swiss-Prot / TrEMBL filtering.
- `SequenceRecord` dataclass in `biocurator.providers.base` — typed container returned by
  `fetch_metadata` and `download`; replaces the previous untyped `dict[str, Any]`.
  Fields: `id`, `accession`, `database`, `title`, `organism`, `sequence_length`,
  `sequence`, `description`, `create_date`, `update_date`, `taxonomy_id`, `authors`,
  `journal`, `downloaded`, `quality_score`.

### Changed

- Provider modules reorganised into per-provider subpackages:
  - `biocurator.providers.ncbi` is now a package (`ncbi/`) with `criteria.py`,
    `query_builders.py`, and `searcher.py`; the old flat `ncbi.py`, `ncbi_criteria.py`,
    and `ncbi_query_builders.py` are removed.
  - `biocurator.providers.uniprot` is now a package (`uniprot/`) with `criteria.py`,
    `query_builders.py`, and `searcher.py`; the old flat `uniprot.py` is removed.
  - `biocurator.providers.__init__` preserves the same public API — all previously
    exported names continue to work from `biocurator.providers`.
- Test files reorganised to mirror source structure: `tests/providers/ncbi/` and
  `tests/providers/uniprot/` subpackages with per-concern modules (`test_criteria.py`,
  `test_query_builders.py`, `test_searcher.py`, `test_apikey.py`).
- `DatabaseSearcher` is now generic (`DatabaseSearcher[C]` where `C` is bound to
  `SearchCriteria`). Concrete searchers declare their criteria type
  (`NCBISearcher(DatabaseSearcher[NCBISearchCriteria])`), eliminating all
  `# type: ignore[override]` suppressions on method signatures.
- `NCBISearcher.build_query` delegates to `get_builder(criteria.database).build(criteria)`
  instead of maintaining its own query-construction logic; database-specific field tags now
  live in the corresponding `QueryBuilder` subclass.
- `SearchCriteria` base class no longer carries NCBI-specific fields (`sequence_type`,
  `taxonomy_filter`, `location`); these are now on `NCBISearchCriteria` only, keeping the
  base class provider-agnostic.

### Fixed

- `Biocurator.run_job` was constructing a bare `SearchCriteria` object for the NCBI
  provider, which would raise `AttributeError: 'SearchCriteria' object has no attribute
  'database'` at runtime. It now constructs `NCBISearchCriteria` for `"ncbi"` and
  `UniProtSearchCriteria` for `"uniprot"`.

## [0.1.1] - 2026-05-16

### Added

- `--debug` global flag on `biocurator` — enables INFO-level stdout logging via
  `enable_verbose_logging()` across all subcommands.
- `--verbose` / `-v` flag on `biocurator run` — attaches an INFO-level handler
  to the root logger so progress messages are printed during a run.
  Format: `YYYY-MM-DD HH:MM:SS  LEVEL     message`.
- `enable_verbose_logging(console=None)` in `biocurator.utils.logging` — public
  helper that wires up the verbose handler; when a `rich.console.Console` is
  passed, a `RichHandler` is used so log lines are coordinated with any active
  Rich live display and never overlap with the progress bar; falls back to a
  plain stdout `StreamHandler` when called without a console; safe to call
  multiple times (duplicate handlers are not added).

### Fixed

- `biocurator_output/` directory is no longer created on startup. `Biocurator`
  used to call `mkdir` unconditionally in `__init__`; directories are now
  created lazily only when a method actually writes files. The output location
  is controlled by `export.outdir` in the job config (per-job) or the new
  `--outdir` CLI flag.
- `--version` flag now correctly prints the current version and exits when
  invoked without a subcommand; previously `no_args_is_help=True` caused Typer
  to show help instead of running the callback. Fixed by attaching a Click-level
  `callback` with `is_eager=True` directly to the option so it fires at parse
  time before command dispatch.
- `--debug` flag now uses `enable_verbose_logging()` instead of
  `setup_development_logging()`, preventing the same Rich progress bar overlap
  that was fixed for `--verbose`.
- `NCBISearcher.fetch_metadata` stored sequence length under `"length"` but
  `SequenceFilter.filter_by_criteria` checked `"sequence_length"`, causing every
  sequence to evaluate as length 0 and be dropped by any `min_length`/`max_length`
  filter. Renamed the key to `"sequence_length"` to match the filter.
- `SequenceFilter.filter_by_criteria` applied the organism post-filter even when
  metadata records had an empty `organism` field. NCBI's `esummary` endpoint does
  not return an `Organism` field, so every record received `organism: ""` and was
  incorrectly rejected. The filter now skips when the field is unpopulated.
- `SequenceFilter.filter_by_criteria` applied the quality filter to pre-download
  metadata records, which lack sequence data. `__calculate_quality_score` returned
  `0.0` for any record without a `"sequence"` key, causing all records to fail any
  non-zero threshold. Quality filtering is now deferred to after `download()` via
  the new `SequenceFilter.apply_quality_filter` method, which `Biocurator.run_job`
  calls on the downloaded sequence set.

## [0.1.0] - 2026-05-16

### Added

- `biocurator init` CLI command — generates a starter YAML config file with `--template basic` (default) or `--template advanced` options; supports `--output` to write directly to a file
- `biocurator run` CLI command — executes curation jobs from a YAML config file; supports `--jobs` to target specific jobs and `--dry-run` to preview without downloading
- `Biocurator.run_job(job_config, progress_callback)` method — runs a single job through search → filter → download → export phases; accepts an optional callback for progress reporting
- `Biocurator._export(export_config)` method — writes FASTA, CSV, and JSON output files from the current sequence set
- `biocurator.config.schema` module — typed dataclasses (`GlobalConfig`, `JobConfig`, `SearchConfig`, `FilterConfig`, `ExportConfig`) for validated, structured configuration
- `biocurator.config.loader.ConfigLoader` — loads and validates YAML config files into `GlobalConfig`; raises typed exceptions for missing fields
- `biocurator.exceptions` module — exception hierarchy (`BiocuratorError`, `ConfigNotFoundError`, `InvalidConfigError`, `JobNotFoundError`, `DatabaseSearchError`, `DownloadError`, `ExportError`)
- `NCBISearcher` and `UniProtSearcher` — database searchers implementing `search`, `fetch_metadata`, and `download` against NCBI E-utilities and UniProt REST API
- `SequenceFilter.filter_by_criteria` — filters sequence metadata by length, organism, location, exclusion terms, taxonomy, and quality score
- Rich progress bars in `biocurator run` with per-phase updates (search / filter / download / export)
- Test suite (32 tests) covering exceptions, config schema, config loader, curator, and CLI commands

### Changed

- `SearchCriteria.quality_threshold` type corrected from `Optional[str]` to `Optional[float]`

### Removed

- Extraction logic specific to ASFV genomes (now superseded by the generic config-driven pipeline)

[Unreleased]: https://github.com/dagsdags212/biocurator/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/dagsdags212/biocurator/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/dagsdags212/biocurator/releases/tag/v0.1.0
