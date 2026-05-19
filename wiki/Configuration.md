# Configuration

A biocurator config file is a YAML file with two top-level keys: `email` and `jobs`.

```yaml
email: your@email.com   # required

jobs:
  <job-name>:
    search: ...
    filter: ...
    export: ...
```

You can define as many jobs as you need in one file. Each job runs independently.

---

## Top level

| Field | Required | Description |
|-------|----------|-------------|
| `email` | Yes | Used by NCBI to identify your requests. Required even if you only query UniProt. |
| `jobs` | Yes | Map of job name → job config. |

---

## `search` block

Controls what to search for and where.

```yaml
search:
  databases: [ncbi]           # required
  organism: "SARS-CoV-2"
  sequence_type: nucleotide
  keywords: ["complete genome"]
  max_results: 100
  exclude_terms: [synthetic]
  location: null
  taxonomy_filter: null
  date_range:
    start: "2020/01/01"
    end: "2024/12/31"
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `databases` | list | — | Required. `ncbi`, `uniprot`, or both. |
| `organism` | string | null | Organism name, e.g. `"E. coli"`, `"Homo sapiens"`. |
| `sequence_type` | string | `nucleotide` | `nucleotide`, `protein`, or `sra`. |
| `keywords` | list | `[]` | Terms AND-joined into the search query. |
| `max_results` | int | `100` | Maximum number of sequences to return. |
| `exclude_terms` | list | `[]` | Terms that must NOT appear in results. |
| `location` | string | null | Geographic filter, e.g. `"Philippines"`. |
| `taxonomy_filter` | string | null | Taxon name or NCBI taxonomy ID. |
| `date_range.start` | string | null | Earliest submission date, format `YYYY/MM/DD`. |
| `date_range.end` | string | null | Latest submission date, format `YYYY/MM/DD`. |

### Supported databases

```yaml
databases: [ncbi]              # NCBI only
databases: [uniprot]           # UniProt only
databases: [ncbi, uniprot]     # both
```

---

## `filter` block

Post-search filters applied to the result set before downloading.

```yaml
filter:
  min_length: 29000
  max_length: null
  exclude_terms: [partial, predicted]
  quality_threshold: 0.9
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `min_length` | int | null | Drop sequences shorter than this (bp for nucleotide, aa for protein). |
| `max_length` | int | null | Drop sequences longer than this. |
| `exclude_terms` | list | `[]` | Drop any record whose title/description contains one of these terms. |
| `quality_threshold` | float | null | `0.0`–`1.0`. Filters on N/X content after download; `0.9` means ≤10% ambiguous bases. |

All filter fields are optional. An empty `filter: {}` block passes everything through.

---

## `export` block

Controls output location and file formats.

```yaml
export:
  outdir: results/covid
  formats: [fasta, csv, json]
  prefix: sars_cov2
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `outdir` | string | `results` | Directory where output files are written. Created if it does not exist. |
| `formats` | list | `[fasta]` | One or more of: `fasta`, `csv`, `json`. |
| `prefix` | string | `biocurator` | Filename prefix. Files are named `<prefix>_sequences.fasta`, `<prefix>_metadata.csv`, etc. |

---

## Minimal valid config

Only `email`, `search.databases`, and one job name are strictly required. Everything else has a sensible default:

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

This searches NCBI for up to 100 human nucleotide sequences and writes `results/biocurator_sequences.fasta`.

---

## Full example with all fields

```yaml
email: researcher@example.com

jobs:
  complete-example:
    search:
      databases: [ncbi, uniprot]
      organism: "Mycobacterium tuberculosis"
      sequence_type: protein
      keywords: ["drug resistance", "efflux pump"]
      max_results: 200
      exclude_terms: [hypothetical, putative, partial]
      location: null
      taxonomy_filter: "1773"          # NCBI taxon ID for M. tuberculosis
      date_range:
        start: "2015/01/01"
        end: "2025/12/31"
    filter:
      min_length: 200
      max_length: 1200
      exclude_terms: [fragment]
      quality_threshold: 0.95
    export:
      outdir: results/mtb_efflux
      formats: [fasta, csv, json]
      prefix: mtb_efflux
```

---

Next: [[CLI Reference]]
