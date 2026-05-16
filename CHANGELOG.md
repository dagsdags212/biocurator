# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/dagsdags212/biocurator/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/dagsdags212/biocurator/releases/tag/v0.1.0
