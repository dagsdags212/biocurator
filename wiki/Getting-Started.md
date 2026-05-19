# Getting Started

This page walks you through your first complete pipeline — from installation to downloaded sequences — in four steps.

## Step 1 — Generate a config file

```bash
biocurator init --output config.yaml
```

This creates a minimal `config.yaml` in your current directory:

```yaml
email: your@email.com

jobs:
  my-job:
    search:
      databases: [ncbi]
      organism: "Your organism"
      sequence_type: nucleotide
      keywords: []
      max_results: 100
    filter:
      min_length: null
      max_length: null
    export:
      outdir: results
      formats: [fasta, csv]
      prefix: output
```

Want all available fields? Use the advanced template:

```bash
biocurator init --template advanced --output config.yaml
```

## Step 2 — Edit the config

Open `config.yaml` in any text editor. Set your email (required for NCBI access) and describe the sequences you want.

Here is a concrete example that fetches complete SARS-CoV-2 genomes:

```yaml
email: researcher@example.com

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

## Step 3 — Preview with dry-run

Before downloading anything, verify the config is valid and see what jobs would run:

```bash
biocurator run config.yaml --dry-run
```

Output:
```
Dry run — 1 job(s) would execute:
  • covid-genomes  databases=['ncbi']
```

If there is a typo or missing field, biocurator reports the error here instead of failing mid-download.

## Step 4 — Run

```bash
biocurator run config.yaml
```

biocurator shows a live progress bar as it moves through each phase:

```
[covid-genomes] search   ████████░░  3/4  0:00:04
```

When it finishes, a summary table is printed:

```
        Run Summary
┌──────────────┬────────┬──────────┐
│ Job          │ Status │ Output   │
├──────────────┼────────┼──────────┤
│ covid-genomes│ done   │ 2 file(s)│
└──────────────┴────────┴──────────┘
```

## Where are the output files?

For the example above, biocurator writes:

```
results/
└── covid/
    ├── sars_cov2_sequences.fasta
    └── sars_cov2_metadata.csv
```

See [[Output Files]] for a full description of each format.

## What's next?

- Add more jobs to the same config — see [[Examples]]
- Run only specific jobs: `biocurator run config.yaml --jobs covid-genomes`
- See every config option: [[Configuration]]
- Use biocurator from Python: [[Python API]]
