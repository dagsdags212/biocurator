# biocurator

A config-driven framework for curating biological sequence datasets from various databases. Define your search, filter, and export parameters in a YAML file; `biocurator` handles the rest.

## Features

- **Multi-database search** — NCBI (nucleotide, protein, SRA) and UniProt
- **Streaming Architecture** — memory-efficient processing of large datasets
- **Robustness** — automatic retries with exponential backoff for API calls
- **Typed config schema** — validated YAML with sensible defaults
- **Flexible filtering** — length, quality score, organism, keywords, date range
- **Multiple export formats** — FASTA, CSV, JSON
- **Rich CLI** — progress bars, dry-run mode, per-job filtering

## Supported Databases

| Database | Entrez / REST databases |
|----------|------------------------|
| NCBI | nuccore, nucleotide, protein, sra, pubmed, pmc, gene, taxonomy, and more |
| UniProt | Swiss-Prot (reviewed) and TrEMBL (unreviewed) protein entries |

## Scalability & Robustness

`biocurator` is designed for high-throughput curation:
- **Streaming:** Sequences are processed one-by-one and streamed directly to disk, allowing you to curate thousands of sequences without exhausting system memory.
- **NCBI History Server:** Automatically uses the NCBI History Server (`WebEnv`) for scalable and stable data retrieval from large search results.
- **Retry Logic:** Built-in exponential backoff retries for all network operations to handle transient API failures gracefully.

## Installation

Requires Python 3.13+.

```bash
# With uv (recommended)
uv pip install biocurator

# With pip
pip install biocurator
```

## Quick Start

### 1. Generate a config file

```bash
biocurator init --output config.yaml
```

This writes a starter YAML to `config.yaml`. Use `--template advanced` to include all optional fields:

```bash
biocurator init --template advanced --output config.yaml
```

### 2. Edit the config

```yaml
email: your@email.com

jobs:
  covid-genomes:
    search:
      databases: [ncbi]
      organism: "SARS-CoV-2"
      sequence_type: nucleotide
      keywords: ["complete genome"]
      max_results: 50
    filter:
      min_length: 29000
      quality_threshold: 0.8
    export:
      outdir: results/covid
      formats: [fasta, csv]
      prefix: sars_cov2
```

### 3. Run a dry-run to preview

```bash
biocurator run config.yaml --dry-run
```

```
Dry run — 1 job(s) would execute:
  • covid-genomes  databases=['ncbi']
```

### 4. Execute

```bash
biocurator run config.yaml
```

## Config Reference

Every config file has a top-level `email` (required for NCBI access) and a `jobs` map where each key is the job name.

```yaml
email: your@email.com # required

jobs:
  <job-name>:
    search:
      databases: [ncbi] # required: ncbi | uniprot
      organism: null # e.g. "SARS-CoV-2", "E. coli"
      sequence_type: nucleotide # nucleotide | protein | sra
      keywords: [] # AND-joined with other terms
      max_results: 100
      exclude_terms: [] # excluded from search
      location: null # geographic filter, e.g. "Philippines"
      taxonomy_filter: null # taxon name or ID
      date_range:
        start: "2020/01/01" # YYYY/MM/DD
        end: "2024/12/31"
    filter:
      min_length: null # minimum sequence length (bp / aa)
      max_length: null # maximum sequence length (bp / aa)
      exclude_terms: [] # excluded from title/description
      quality_threshold: null # 0.0–1.0; filters on N/X content
    export:
      outdir: results # output directory (created if absent)
      formats: [fasta] # fasta | csv | json
      prefix: biocurator # filename prefix for output files
```

Defaults apply to any omitted field, so a minimal job only needs `search.databases`:

```yaml
email: your@email.com

jobs:
  simple:
    search:
      databases: [ncbi]
      organism: "Homo sapiens"
    filter: {}
    export: {}
```

## CLI Reference

### `biocurator init`

Generate a starter config file.

```
Usage: biocurator init [OPTIONS]

Options:
  -o, --output TEXT    Write config to this file instead of stdout
  -t, --template TEXT  Template to use: basic (default) or advanced
```

### `biocurator run`

Run all jobs defined in a config file.

```
Usage: biocurator run [OPTIONS] CONFIG

Arguments:
  CONFIG  Path to the YAML config file  [required]

Options:
  -j, --jobs TEXT  Comma-separated job names to run (default: all)
  --dry-run        Validate config and preview jobs without downloading
```

**Run only specific jobs:**

```bash
biocurator run config.yaml --jobs covid-genomes,spike-proteins
```

**Dry-run before committing:**

```bash
biocurator run config.yaml --dry-run
```

## Usage Examples

### Viral genome surveillance

Collect complete SARS-CoV-2 genomes deposited in 2024, filtered for quality:

```yaml
email: researcher@uni.edu

jobs:
  sars-cov2-2024:
    search:
      databases: [ncbi]
      organism: "SARS-CoV-2"
      sequence_type: nucleotide
      keywords: ["complete genome"]
      max_results: 500
      exclude_terms: [synthetic, artificial, recombinant]
      date_range:
        start: "2024/01/01"
        end: "2024/12/31"
    filter:
      min_length: 29000
      quality_threshold: 0.9
    export:
      outdir: results/sars_2024
      formats: [fasta, csv]
      prefix: sars_cov2_2024
```

### Antibiotic resistance genes

Collect beta-lactamase nucleotide sequences from NCBI:

```yaml
email: researcher@uni.edu

jobs:
  beta-lactamase:
    search:
      databases: [ncbi]
      sequence_type: nucleotide
      keywords: ["beta-lactamase", "bla gene"]
      max_results: 300
      exclude_terms: [partial, predicted]
    filter:
      min_length: 500
      max_length: 3000
    export:
      outdir: results/amr
      formats: [fasta, csv, json]
      prefix: bla_genes
```

### Multi-database protein family study

Search both NCBI and UniProt for a protein family in the same job:

```yaml
email: researcher@uni.edu

jobs:
  cytochrome-p450:
    search:
      databases: [ncbi, uniprot]
      sequence_type: protein
      keywords: ["cytochrome P450", "CYP"]
      max_results: 200
    filter:
      min_length: 300
      quality_threshold: 0.8
    export:
      outdir: results/cyp450
      formats: [fasta, csv]
      prefix: cyp450
```

### Multiple independent jobs in one run

```yaml
email: researcher@uni.edu

jobs:
  spike-proteins:
    search:
      databases: [uniprot]
      organism: "SARS-CoV-2"
      sequence_type: protein
      keywords: ["spike glycoprotein"]
      max_results: 100
    filter:
      min_length: 1200
    export:
      outdir: results/spike
      formats: [fasta]
      prefix: spike

  nucleocapsid-proteins:
    search:
      databases: [uniprot]
      organism: "SARS-CoV-2"
      sequence_type: protein
      keywords: ["nucleocapsid protein"]
      max_results: 100
    filter:
      min_length: 400
    export:
      outdir: results/ncap
      formats: [fasta]
      prefix: ncap
```

Run them together or selectively:

```bash
# All jobs
biocurator run config.yaml

# Only one
biocurator run config.yaml --jobs spike-proteins
```

## Python API

You can drive curation from Python directly using `Biocurator.run_job()`:

```python
from biocurator.core.curator import Biocurator
from biocurator.config.schema import (
    JobConfig, SearchConfig, FilterConfig, ExportConfig,
)

job = JobConfig(
    name="my-job",
    search=SearchConfig(
        databases=["ncbi"],
        organism="SARS-CoV-2",
        sequence_type="nucleotide",
        keywords=["complete genome"],
        max_results=10,
    ),
    filter=FilterConfig(min_length=29000, quality_threshold=0.8),
    export=ExportConfig(outdir="results", formats=["fasta", "csv"], prefix="sars"),
)

curator = Biocurator(email="your@email.com")
output_files = curator.run_job(job)
# {"fasta": PosixPath("results/sars_sequences.fasta"), "csv": PosixPath("results/sars_metadata.csv")}
```

Progress callbacks let you integrate with your own UI:

```python
def on_progress(phase: str, current: int, total: int):
    print(f"[{phase}] {current}/{total}")

curator.run_job(job, progress_callback=on_progress)
```

Load a config file programmatically:

```python
from biocurator.config.loader import ConfigLoader

config = ConfigLoader.load("config.yaml")
curator = Biocurator(email=config.email)

for job in config.jobs:
    output_files = curator.run_job(job)
    print(f"{job.name}: {list(output_files)}")
```

## Provider internals

Each database provider exposes a `QueryBuilder` that translates search criteria into a database-specific query string. You can use these directly if you need the query without running the full pipeline:

```python
from biocurator.providers.ncbi import NCBISearchCriteria, get_builder
from biocurator.providers.base import NCBIDatabase

criteria = NCBISearchCriteria(
    database=NCBIDatabase.PUBMED,
    organism="Homo sapiens",
    keywords=["CRISPR"],
)
builder = get_builder(NCBIDatabase.PUBMED)
print(builder.build(criteria))
# '"Homo sapiens"[MeSH Terms] AND "CRISPR"[Title/Abstract]'

# Inspect available search fields
for field, desc in builder.available_fields().items():
    print(f"{field}: {desc}")

# Get records (returns an iterator)
searcher = ProviderRegistry.get("ncbi", DatabaseConfig(name="NCBI"), "your@email.com")
ids = searcher.search(criteria)
for record in searcher.fetch_metadata(ids, criteria):
    print(record.accession)
```

For UniProt:

```python
from biocurator.providers.uniprot import UniProtQueryBuilder, UniProtSearchCriteria

criteria = UniProtSearchCriteria(organism="Mus musculus", reviewed=True)
query = UniProtQueryBuilder().build(criteria)
# 'organism:"Mus musculus" AND reviewed:true'
```

## Output Files

| File                       | Format | Contents                                 |
| -------------------------- | ------ | ---------------------------------------- |
| `<prefix>_sequences.fasta` | FASTA  | Downloaded sequences                     |
| `<prefix>_metadata.csv`    | CSV    | Per-sequence metadata                    |
| `<prefix>_metadata.json`   | JSON   | Per-sequence metadata (machine-readable) |

## Troubleshooting

**No sequences returned**

- Broaden `keywords`, remove `exclude_terms`, or increase `max_results`
- Verify the organism name matches NCBI/UniProt taxonomy exactly

**NCBI rate-limit errors**

- NCBI enforces 3 requests/second without an API key; the searcher already respects this, but heavy jobs may be slow

**`InvalidConfigError: 'email' is required`**

- Add `email: your@email.com` at the top level of the YAML

**`ConfigNotFoundError`**

- Check the path passed to `biocurator run` — use `--dry-run` to validate before downloading

**Enable debug logging**

```bash
biocurator --debug run config.yaml
```

## License

MIT

---

## Additional CLI Commands

### `biocurator status`

Probe configured database providers and display their health status.

```
biocurator status [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--config PATH` / `-c PATH` | `config.yaml` | Path to the YAML config file |

Reads each provider from the config, runs a lightweight connectivity probe, and renders a Rich table with four columns: **Provider**, **Status** (UP/DOWN), **Response Time**, and **Breaker State** (`closed`, `half_open`, or `open`).

```bash
biocurator status
biocurator status --config biocurator_config.yaml
```

### `biocurator jobs`

List all curation jobs defined in the config file.

```
biocurator jobs [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--config PATH` / `-c PATH` | `biocurator_config.yaml` | Path to the YAML config file |

Renders a Rich table with columns: **Job Name**, **Databases**, **Organism**, **Max Results**, **Output Dir**, **Formats**.

```bash
biocurator jobs
biocurator jobs --config my_config.yaml
```

### `biocurator files`

List downloaded output files for one or all jobs, with optional SHA-256 checksum verification.

```
biocurator files [JOB_NAME] [OPTIONS]
```

| Argument / Option | Default | Description |
|-------------------|---------|-------------|
| `JOB_NAME` | *(all jobs)* | Job name to inspect (omit for a summary of all jobs) |
| `--config PATH` / `-c PATH` | `biocurator_config.yaml` | Path to the YAML config file |
| `--verify` | `false` | Re-read files from disk and verify SHA-256 checksums against the manifest |

When called without a job name, shows a summary row per job (output dir, file count, record count, manifest present/absent). When called with a job name, shows per-file details (filename, format, size, record count, first 12 hex digits of SHA-256).

```bash
# Summary of all jobs
biocurator files

# Detail for one job
biocurator files my-job

# Verify checksums for all jobs
biocurator files --verify

# Verify checksums for one job
biocurator files my-job --verify
```

## Circuit Breaker Support

`Biocurator` accepts optional `global_retry` (`RetryConfig`) and `global_breaker` (`BreakerConfig`) parameters that control retry and circuit breaker behaviour across all providers. When a provider exceeds its failure threshold the circuit breaker opens, preventing further requests until the provider recovers. Use `biocurator status` to inspect the current circuit breaker state for each configured provider.
