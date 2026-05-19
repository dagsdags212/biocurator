# Installation

## Requirements

- Python 3.13 or newer

## Install with uv (recommended)

[uv](https://github.com/astral-sh/uv) is the fastest way to get biocurator installed:

```bash
uv pip install biocurator
```

## Install with pip

```bash
pip install biocurator
```

## Install from source

If you want to run the latest unreleased code:

```bash
git clone https://github.com/dagsdags212/biocurator.git
cd biocurator
uv pip install -e .
```

## Verify the installation

```bash
biocurator --version
```

Expected output:
```
biocurator 0.1.1
```

## Dependencies

biocurator installs these packages automatically:

| Package | Purpose |
|---------|---------|
| biopython | Sequence parsing and FASTA I/O |
| requests | HTTP calls to NCBI and UniProt APIs |
| pandas | Metadata table handling |
| pyyaml | Config file parsing |
| rich | Progress bars and formatted output |
| typer | CLI framework |

---

Next: [[Getting Started]]
