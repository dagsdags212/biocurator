<!-- generated-by: gsd-doc-writer -->
# Configuration Reference

Biocurator is driven entirely by a YAML configuration file. No environment variables are required at runtime. The file defines your NCBI email address, optional global resilience settings, and one or more named curation jobs, each specifying what to search for, how to filter results, and where to export output.

Generate a starter config with:

```bash
biocurator init
```

This writes a `biocurator_config.yaml` file in the current directory. Pass `--config <path>` to any CLI command to use a different filename.

---

## Config File Format Overview

Top-level structure:

```yaml
email: your@email.com        # Required — sent to NCBI with every API call
retry:                       # Optional — global retry settings
  max_attempts: 3
breaker:                     # Optional — global circuit breaker settings
  fail_max: 5
jobs:                        # Required — dict of named curation jobs
  job-name:
    search: { ... }
    filter: { ... }          # Optional
    export: { ... }
```

The config is loaded by `ConfigLoader.load(path)`. Validation is strict: a missing `email` or empty `jobs` block raises `InvalidConfigError` on startup.

---

## Top-Level Fields

| Field     | Type                          | Required | Description |
|-----------|-------------------------------|----------|-------------|
| `email`   | `str`                         | Yes      | Contact email sent to NCBI Entrez with every API request. Required by NCBI usage policy. |
| `jobs`    | `dict[str, JobConfig]`        | Yes      | Mapping of job name → job definition. At least one entry required. |
| `retry`   | `RetryConfig`                 | No       | Global retry defaults applied to all providers unless overridden per-job. |
| `breaker` | `BreakerConfig`               | No       | Global circuit breaker defaults applied to all providers unless overridden per-job. |

### `email`

```yaml
email: researcher@institution.edu
```

NCBI sets this as `Bio.Entrez.email` before every Entrez call. Without a valid email, NCBI may throttle or block automated requests.

---

## `retry` — Global Retry Configuration (`RetryConfig`)

Optional top-level block. Values defined here are used as defaults for all providers. Per-job values in `search.retry` override these.

| Field            | Type    | Default | Description |
|------------------|---------|---------|-------------|
| `max_attempts`   | `int`   | `3`     | Total number of attempts (1 initial + N-1 retries) before raising. |
| `backoff_factor` | `float` | `2.0`   | Multiplier applied to the delay after each failed attempt (exponential backoff). |
| `max_delay`      | `int`   | `60`    | Maximum delay in seconds between retries regardless of backoff calculation. |
| `timeout`        | `int`   | `30`    | Per-request timeout in seconds. |

```yaml
retry:
  max_attempts: 5
  backoff_factor: 2.0
  max_delay: 120
  timeout: 30
```

---

## `breaker` — Global Circuit Breaker Configuration (`BreakerConfig`)

Optional top-level block. Uses `pybreaker.CircuitBreaker` internally. Per-job values in `search.breaker` override these.

| Field                    | Type  | Default | Description |
|--------------------------|-------|---------|-------------|
| `fail_max`               | `int` | `5`     | Number of consecutive failures before the circuit opens (blocks further calls). |
| `recovery_timeout`       | `int` | `60`    | Seconds to wait in OPEN state before allowing a probe request (HALF-OPEN). |
| `half_open_max_successes`| `int` | `1`     | Successful probes needed in HALF-OPEN state to close the circuit. |

```yaml
breaker:
  fail_max: 3
  recovery_timeout: 30
  half_open_max_successes: 2
```

Circuit breaker states: **CLOSED** (normal) → **OPEN** (blocking after `fail_max` failures) → **HALF-OPEN** (probe) → **CLOSED** (on success). Use `biocurator status` to inspect live state.

---

## `jobs` — Curation Job Configuration

`jobs` is a YAML mapping where each key is the job name (used in `--jobs` CLI filtering and log output). Each value is a `JobConfig` with the following fields:

| Field    | Required | Description |
|----------|----------|-------------|
| `search` | Yes      | What to search for and from which databases. |
| `filter` | No       | Post-search filtering criteria. |
| `export` | No       | Output directory, formats, and filename prefix. |

---

## `search` — Search Configuration (`SearchConfig`)

| Field             | Type            | Required | Default        | Description |
|-------------------|-----------------|----------|----------------|-------------|
| `databases`       | `list[str]`     | Yes      | —              | Providers to query. Valid values: `ncbi`, `uniprot`. |
| `organism`        | `str`           | No       | `null`         | Organism name (e.g. `"SARS-CoV-2"`, `"Homo sapiens"`). |
| `sequence_type`   | `str`           | No       | `"nucleotide"` | Molecule type filter: `nucleotide` or `protein`. |
| `keywords`        | `list[str]`     | No       | `[]`           | Search terms AND-joined with other criteria. |
| `max_results`     | `int`           | No       | `100`          | Maximum records to retrieve per database. |
| `date_range`      | `dict`          | No       | `null`         | Date window with `start` and `end` keys (`YYYY/MM/DD`). |
| `exclude_terms`   | `list[str]`     | No       | `[]`           | Terms excluded from results (NOT clauses in query). |
| `location`        | `str`           | No       | `null`         | Geographic location filter (NCBI-specific). |
| `taxonomy_filter` | `str`           | No       | `null`         | NCBI taxonomy ID or name (e.g. `"9606"` for human). |
| `preflight_check` | `bool`          | No       | `false`        | Run a connectivity check before executing the job. |
| `retry`           | `dict[str, RetryConfig]` | No | `null`    | Per-database retry overrides (e.g. `ncbi:`, `uniprot:`). |
| `breaker`         | `dict[str, BreakerConfig]` | No | `null`  | Per-database circuit breaker overrides. |

### `date_range` format

```yaml
date_range:
  start: "2020/01/01"
  end: "2024/12/31"
```

### Per-job retry/breaker overrides

```yaml
search:
  databases: [ncbi, uniprot]
  retry:
    ncbi:
      max_attempts: 5
      backoff_factor: 3.0
    uniprot:
      max_attempts: 2
  breaker:
    ncbi:
      fail_max: 10
      recovery_timeout: 120
```

Per-database values are merged with global defaults: per-db wins, then global, then built-in defaults.

---

## `filter` — Filter Configuration (`FilterConfig`)

Optional. When present, the full result set is passed through `SequenceFilter.filter_by_criteria()` before export.

| Field               | Type        | Default | Description |
|---------------------|-------------|---------|-------------|
| `min_length`        | `int`       | `null`  | Minimum sequence length in bp/aa (inclusive). |
| `max_length`        | `int`       | `null`  | Maximum sequence length in bp/aa (inclusive). |
| `exclude_terms`     | `list[str]` | `[]`    | Discard records whose title/description contains any of these terms. |
| `quality_threshold` | `float`     | `null`  | Minimum quality score 0.0–1.0. Records below this are dropped. |

```yaml
filter:
  min_length: 100
  max_length: 5000
  exclude_terms: [partial, fragment]
  quality_threshold: 0.75
```

---

## `export` — Export Configuration (`ExportConfig`)

| Field     | Type        | Default          | Description |
|-----------|-------------|------------------|-------------|
| `outdir`  | `str`       | `"results"`      | Output directory path. Created if it does not exist. |
| `formats` | `list[str]` | `["fasta"]`      | Output formats: `fasta`, `csv`, `json`. Multiple formats produce multiple files in one pass. |
| `prefix`  | `str`       | `"biocurator"`   | Filename prefix. Files are named `{prefix}.{format}`. |

### Output file formats

| Value   | Filename                | Contents |
|---------|-------------------------|----------|
| `fasta` | `{prefix}.fasta`        | Standard FASTA with `>accession description` headers. |
| `csv`   | `{prefix}.csv`          | CSV with one row per record: accession, title, organism, length, quality score, dates. |
| `json`  | `{prefix}.json`         | JSON array of record objects, finalized when the exporter closes. |

A `manifest.json` and `manifest-sha256.txt` are also written to `outdir` after each job for checksum verification via `biocurator files --verify`.

---

## Complete Annotated Example

```yaml
# biocurator_config.yaml
email: researcher@institution.edu

# Optional global resilience settings — apply to all providers
retry:
  max_attempts: 3
  backoff_factor: 2.0
  max_delay: 60
  timeout: 30

breaker:
  fail_max: 5
  recovery_timeout: 60
  half_open_max_successes: 1

jobs:
  # ---------------------------------------------------------------
  # Job 1: NCBI + UniProt search for cytochrome P450 proteins
  # ---------------------------------------------------------------
  cytochrome-p450:
    search:
      databases: [ncbi, uniprot]
      sequence_type: protein
      keywords: ["cytochrome P450", "CYP"]
      max_results: 200
      # Per-job retry override for NCBI only
      retry:
        ncbi:
          max_attempts: 5
          backoff_factor: 3.0
    filter:
      min_length: 300
      quality_threshold: 0.8
    export:
      outdir: results/cyp450
      formats: [fasta, csv]
      prefix: cyp450

  # ---------------------------------------------------------------
  # Job 2: SARS-CoV-2 complete genomes, date-restricted
  # ---------------------------------------------------------------
  covid-genomes:
    search:
      databases: [ncbi]
      organism: "SARS-CoV-2"
      sequence_type: nucleotide
      keywords: ["complete genome"]
      max_results: 50
      date_range:
        start: "2020/01/01"
        end: "2026/05/15"
    filter:
      min_length: 29000
      quality_threshold: 0.8
    export:
      outdir: results/covid
      formats: [fasta, csv, json]
      prefix: sars_cov2
```

---

## Validation Errors

| Condition | Error |
|-----------|-------|
| Config file path not found | `ConfigNotFoundError: "Config file not found: {path}"` |
| YAML syntax error | `InvalidConfigError: "Invalid YAML: {detail}"` |
| `email` missing or empty | `InvalidConfigError: "'email' is required at the top level"` |
| `jobs` missing or not a dict | `InvalidConfigError: "'jobs' must be a non-empty mapping"` |
| `search.databases` missing in a job | `InvalidConfigError: "Job '{name}': 'search.databases' is required"` |

---

## NCBI Email Requirement

NCBI Entrez requires all automated clients to identify themselves with a valid email address (`Bio.Entrez.email`). Without it, NCBI may throttle requests. The `email` field at the top level of the config fulfills this requirement.
