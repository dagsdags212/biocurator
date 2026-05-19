# Output Files

biocurator writes up to three files per job, depending on which formats you request.

## File naming

All output filenames follow the pattern `<prefix>_<type>.<ext>`, where `prefix` is set in the `export` block of your config.

| Format | Filename | Contents |
|--------|----------|----------|
| `fasta` | `<prefix>_sequences.fasta` | Sequences in FASTA format |
| `csv` | `<prefix>_metadata.csv` | Per-sequence metadata as a table |
| `json` | `<prefix>_metadata.json` | Per-sequence metadata as JSON |

### Example

For this config:

```yaml
export:
  outdir: results/covid
  formats: [fasta, csv, json]
  prefix: sars_cov2
```

biocurator creates:

```
results/
└── covid/
    ├── sars_cov2_sequences.fasta
    ├── sars_cov2_metadata.csv
    └── sars_cov2_metadata.json
```

The `outdir` directory is created automatically if it does not exist.

---

## FASTA format

Standard FASTA with the accession as the sequence ID:

```
>MN908947.3
ATTAAAGGTTTATACCTTCCCAGGTAACAAACCAACCAACTTTCGATCTCTTGTAGATCT...
>MT019529.1
ATTAAAGGTTTATACCTTCCCAGGTAACAAACCAACCAACTTTCGATCTCTTGTAGATCT...
```

---

## CSV format

One row per sequence. Columns depend on the source database but typically include:

| Column | Description |
|--------|-------------|
| `accession` | Sequence accession number |
| `title` | Record title / description |
| `organism` | Organism name |
| `sequence_length` | Length in bp (nucleotide) or aa (protein) |
| `submission_date` | Date the record was submitted |
| `database` | Source database (`ncbi` or `uniprot`) |

Example rows:

```
accession,title,organism,sequence_length,submission_date,database
MN908947.3,Severe acute respiratory syndrome coronavirus 2 isolate Wuhan-Hu-1,SARS-CoV-2,29903,2020-01-05,ncbi
MT019529.1,Severe acute respiratory syndrome coronavirus 2 isolate 2019-nCoV/USA-WA1/2020,SARS-CoV-2,29882,2020-01-17,ncbi
```

---

## JSON format

Array of objects, same fields as the CSV:

```json
[
  {
    "accession": "MN908947.3",
    "title": "Severe acute respiratory syndrome coronavirus 2 isolate Wuhan-Hu-1",
    "organism": "SARS-CoV-2",
    "sequence_length": 29903,
    "submission_date": "2020-01-05",
    "database": "ncbi"
  },
  {
    "accession": "MT019529.1",
    "title": "Severe acute respiratory syndrome coronavirus 2 isolate 2019-nCoV/USA-WA1/2020",
    "organism": "SARS-CoV-2",
    "sequence_length": 29882,
    "submission_date": "2020-01-17",
    "database": "ncbi"
  }
]
```

---

## Choosing formats

| Use case | Recommended formats |
|----------|-------------------|
| Alignment / phylogenetics | `fasta` |
| Spreadsheet analysis | `csv` |
| Downstream scripting / APIs | `json` |
| Full archival | `fasta`, `csv`, `json` |

```yaml
# Lightweight — sequences only
formats: [fasta]

# Analysis-ready — sequences + tabular metadata
formats: [fasta, csv]

# Full archival
formats: [fasta, csv, json]
```

---

Next: [[Troubleshooting]]
