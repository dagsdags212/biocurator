# biocurator

**biocurator** is a config-driven command-line tool for curating biological sequence datasets. You describe what you want in a YAML file — which databases to search, which organism, what filters to apply, and where to save the results — and biocurator handles the rest.

## Why biocurator?

Building a sequence dataset usually means writing one-off scripts for NCBI or UniProt, manually filtering by length or quality, and juggling output formats. biocurator wraps all of that into a single repeatable workflow:

```
config.yaml  →  biocurator run  →  sequences.fasta + metadata.csv
```

## Supported databases

| Database | Entrez / REST databases |
|----------|------------------------|
| NCBI     | nuccore, nucleotide, protein, sra, pubmed, pmc, gene, taxonomy, and more |
| UniProt  | Swiss-Prot (reviewed) and TrEMBL (unreviewed) protein entries |

## Key features

- **YAML-driven jobs** — reproducible, version-controllable configs
- **Multi-database search** — query NCBI and UniProt in the same job
- **QueryBuilder strategy** — each NCBI database uses the correct field tags automatically
- **Flexible filtering** — length range, quality score, exclusion terms, date range, location, taxonomy
- **Multiple output formats** — FASTA, CSV, JSON
- **Dry-run mode** — preview jobs before downloading anything
- **Selective execution** — run one job from a multi-job config
- **Python API** — embed curation directly in your own scripts
- **Extensible provider system** — add new databases without touching the pipeline

## Quick example

```bash
# 1. Generate a config
biocurator init --output config.yaml

# 2. Preview what will run
biocurator run config.yaml --dry-run

# 3. Download sequences
biocurator run config.yaml
```

## Wiki pages

| Page | What it covers |
|------|---------------|
| [[Installation]] | How to install biocurator |
| [[Getting Started]] | Your first working pipeline, step by step |
| [[Configuration]] | Every config field explained with examples |
| [[CLI Reference]] | All commands, flags, and arguments |
| [[Examples]] | Real-world use cases ready to copy |
| [[Python API]] | Use biocurator from your own Python scripts |
| [[Output Files]] | What files biocurator creates and what is in them |
| [[Troubleshooting]] | Common errors and how to fix them |
| [[Adding a Custom Provider]] | Extend biocurator with a new database |
