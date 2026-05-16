# biocurator

A config-driven framework for curating biological sequence datasets from various databases. Define your search, filter, and export parameters in a YAML file; `biocurator` handles the rest.

## Features

- **Multi-database search** — NCBI (nucleotide, protein, SRA) and UniProt
- **Typed config schema** — validated YAML with sensible defaults
- **Flexible filtering** — length, quality score, organism, keywords, date range
- **Multiple export formats** — FASTA, CSV, JSON
- **Rich CLI** — progress bars, dry-run mode, per-job filtering

## Supported Databases

- NCBI
- UniProt

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
