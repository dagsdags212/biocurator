<!-- generated-by: gsd-doc-writer -->
# Getting Started

This guide walks you through installing Biocurator and running your first curation job.

## Prerequisites

- Python 3.13 or later
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

## Installation

```bash
# With uv (recommended)
uv pip install biocurator

# With pip
pip install biocurator
```

Verify the install:

```bash
biocurator --version
```

## Step 1 — Generate a Config File

```bash
biocurator init
```

This writes a `biocurator_config.yaml` starter file in the current directory. To include all optional fields:

```bash
biocurator init --template advanced
```

## Step 2 — Edit the Config

Open `biocurator_config.yaml` and fill in your details. A minimal working config:

```yaml
email: your@email.com   # required — sent to NCBI with every API call

jobs:
  my-first-job:
    search:
      databases: [ncbi]
      organism: "SARS-CoV-2"
      sequence_type: nucleotide
      keywords: ["complete genome"]
      max_results: 10
    filter:
      min_length: 29000
      quality_threshold: 0.8
    export:
      outdir: results/
      formats: [fasta, csv]
      prefix: sars_cov2
```

See [CONFIGURATION.md](CONFIGURATION.md) for the full field reference.

## Step 3 — Check Provider Connectivity

Before downloading, verify that NCBI and UniProt are reachable:

```bash
biocurator status
```

This shows each provider's UP/DOWN status, response time, and circuit breaker state.

## Step 4 — Preview Results (Optional)

Run a preview to see what records match your search criteria without downloading anything:

```bash
biocurator preview --config biocurator_config.yaml --job my-first-job
```

This renders a table with accession, title, organism, and sequence length for up to 10 matching records per database.

## Step 5 — Run the Job

```bash
biocurator run biocurator_config.yaml
```

To run only one job from a multi-job config:

```bash
biocurator run biocurator_config.yaml --jobs my-first-job
```

To validate your config without downloading anything:

```bash
biocurator run biocurator_config.yaml --dry-run
```

## Step 6 — Inspect Output Files

After a successful run, check what was downloaded:

```bash
biocurator files
```

Or for a specific job:

```bash
biocurator files my-first-job
```

Verify file integrity with SHA-256 checksums:

```bash
biocurator files my-first-job --verify
```

## Output Files

| File | Format | Contents |
|------|--------|----------|
| `{prefix}.fasta` | FASTA | Downloaded sequences |
| `{prefix}.csv` | CSV | Per-sequence metadata |
| `{prefix}.json` | JSON | Machine-readable metadata |
| `manifest.json` | JSON | File list with checksums and record counts |
| `manifest-sha256.txt` | Text | SHA-256 hashes for verification |

## Troubleshooting

**`ConfigNotFoundError`** — The path passed to `biocurator run` does not exist. Check the filename (the default is `biocurator_config.yaml`, not `config.yaml`).

**`InvalidConfigError: 'email' is required`** — Add `email: your@email.com` at the top of the YAML.

**No sequences returned** — Broaden `keywords`, remove `exclude_terms`, or increase `max_results`. Run `biocurator preview` to inspect raw results first.

**NCBI rate-limit errors** — NCBI allows 3 requests/second without an API key. Biocurator uses exponential-backoff retry automatically; reduce `max_results` for large jobs.

**Enable debug logging:**

```bash
biocurator --debug run biocurator_config.yaml
```
