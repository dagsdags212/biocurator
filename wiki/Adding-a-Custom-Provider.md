# Adding a Custom Provider

This guide explains how to clone biocurator, set up a development environment, and add support for a new biological database by implementing a custom provider.

---

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (used for dependency management)
- Git

---

## 1 — Clone and install

```bash
git clone https://github.com/dagsdags212/biocurator.git
cd biocurator
uv sync
```

`uv sync` creates a virtual environment at `.venv/` and installs all dependencies. Verify the install:

```bash
uv run pytest
# 70 passed
```

---

## 2 — How providers work

biocurator uses a **provider registry** to decouple database logic from the pipeline. Each provider is a self-contained Python module that:

1. Subclasses `DatabaseSearcher` (the abstract base class)
2. Implements four methods: `build_query`, `search`, `fetch_metadata`, `download`
3. Calls `ProviderRegistry.register()` at module load to make itself available by name

When the pipeline initialises, it calls `ProviderRegistry.get("ncbi", config, email)` — it never imports a concrete class directly. Adding a new database therefore requires **one new file** and no changes to the pipeline.

### Key classes

| Class | Module | Role |
|-------|--------|------|
| `DatabaseSearcher` | `biocurator.providers.base` | Abstract base — subclass this |
| `DatabaseConfig` | `biocurator.providers.base` | Holds connection settings (URL, rate limit, …) |
| `SearchCriteria` | `biocurator.providers.base` | Structured search parameters passed to every method |
| `ProviderRegistry` | `biocurator.providers.registry` | Global name → class map; call `register()` and `get()` |

### `SearchCriteria` fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `organism` | `str \| None` | `None` | Taxonomic name |
| `sequence_type` | `str` | `"nucleotide"` | e.g. `"nucleotide"`, `"protein"` |
| `keywords` | `list[str]` | `[]` | Free-text keywords |
| `location` | `str \| None` | `None` | Geographic filter, comma-separated |
| `min_length` | `int \| None` | `None` | Minimum sequence length |
| `max_length` | `int \| None` | `None` | Maximum sequence length |
| `start_date` | `str \| None` | `None` | Earliest submission date |
| `end_date` | `str \| None` | `None` | Latest submission date |
| `max_results` | `int` | `100` | Upper bound on returned IDs |
| `exclude_terms` | `list[str]` | `[]` | Terms that must not appear |
| `taxonomy_filter` | `str \| None` | `None` | Additional taxonomic filter |
| `quality_threshold` | `float \| None` | `None` | Minimum quality score (0–1) |

### `DatabaseConfig` fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | — | Human-readable label |
| `base_url` | `str \| None` | `None` | Root API URL |
| `api_key` | `str \| None` | `None` | Optional API key |
| `rate_limit` | `float` | `0.3` | Seconds to sleep between requests |
| `batch_size` | `int` | `20` | IDs per API call |
| `timeout` | `int` | `30` | HTTP timeout in seconds |

---

## 3 — Implement your provider

Create `src/biocurator/providers/<name>.py`. The skeleton below shows every required piece:

```python
# src/biocurator/providers/ensembl.py
import time
from pathlib import Path
from typing import Any

from biocurator.providers.base import DatabaseConfig, DatabaseSearcher, SearchCriteria
from biocurator.providers.registry import ProviderRegistry
from biocurator.utils.logging import get_logger

logger = get_logger(__name__)


class EnsemblSearcher(DatabaseSearcher):
    def __init__(self, config: DatabaseConfig, email: str) -> None:
        super().__init__(config, email)           # sets self.config, self.email, self.session
        self._base_url = config.base_url or "https://rest.ensembl.org"

    # ------------------------------------------------------------------
    # Required — translate SearchCriteria into a query the API understands
    # ------------------------------------------------------------------
    def build_query(self, criteria: SearchCriteria) -> str:
        parts = []
        if criteria.organism:
            parts.append(f"species:{criteria.organism}")
        if criteria.keywords:
            parts.append(" OR ".join(criteria.keywords))
        return " AND ".join(parts)

    # ------------------------------------------------------------------
    # Required — return a list of record IDs
    # ------------------------------------------------------------------
    def search(self, criteria: SearchCriteria) -> list[str]:
        logger.info("Searching Ensembl...")
        query = self.build_query(criteria)
        try:
            response = self.session.get(
                f"{self._base_url}/lookup/symbol/homo_sapiens/{query}",
                headers={"Content-Type": "application/json"},
                timeout=self.config.timeout,
            )
            response.raise_for_status()
            data = response.json()
            ids = [entry["id"] for entry in data.get("results", [])]
            logger.info(f"Found {len(ids)} Ensembl IDs")
            return ids
        except Exception as exc:
            logger.error(f"Ensembl search failed: {exc}")
            return []

    # ------------------------------------------------------------------
    # Required — return metadata dicts for each ID
    # ------------------------------------------------------------------
    def fetch_metadata(self, ids: list[str]) -> list[dict[str, Any]]:
        logger.info(f"Fetching metadata for {len(ids)} Ensembl IDs...")
        results = []
        for ensembl_id in ids:
            try:
                response = self.session.get(
                    f"{self._base_url}/lookup/id/{ensembl_id}",
                    headers={"Content-Type": "application/json"},
                    timeout=self.config.timeout,
                )
                response.raise_for_status()
                entry = response.json()
                results.append({
                    "id": ensembl_id,
                    "accession": ensembl_id,
                    "title": entry.get("display_name", ""),
                    "organism": entry.get("species", ""),
                    "sequence_length": entry.get("end", 0) - entry.get("start", 0),
                    "database": "Ensembl",
                })
                time.sleep(self.config.rate_limit)
            except Exception as exc:
                logger.warning(f"Could not fetch metadata for {ensembl_id}: {exc}")
        return results

    # ------------------------------------------------------------------
    # Required — download sequences and return their metadata
    # ------------------------------------------------------------------
    def download(self, ids: list[str], outdir: Path) -> list[dict[str, Any]]:
        logger.info(f"Downloading {len(ids)} Ensembl sequences...")
        downloaded = []
        for ensembl_id in ids:
            try:
                response = self.session.get(
                    f"{self._base_url}/sequence/id/{ensembl_id}",
                    headers={"Content-Type": "text/plain"},
                    timeout=self.config.timeout,
                )
                response.raise_for_status()
                sequence = response.text.strip()
                downloaded.append({
                    "id": ensembl_id,
                    "accession": ensembl_id,
                    "sequence": sequence,
                    "sequence_length": len(sequence),
                    "downloaded": True,
                })
                time.sleep(self.config.rate_limit)
            except Exception as exc:
                logger.warning(f"Could not download {ensembl_id}: {exc}")
        return downloaded


# Self-register — this line is what makes "ensembl" usable by name.
ProviderRegistry.register("ensembl", EnsemblSearcher)
```

### Rules for `fetch_metadata` return dicts

The pipeline passes these dicts to the filter and export stages. Include at minimum:

| Key | Type | Notes |
|-----|------|-------|
| `id` | `str` | Used to look up records for download |
| `accession` | `str` | Written to FASTA headers and CSV |
| `organism` | `str` | Used by organism-based filters |
| `sequence_length` | `int` | Used by length filters |
| `database` | `str` | Appears in summary reports |

Extra keys are preserved in CSV/JSON output and ignored elsewhere.

---

## 4 — Register the provider

Open `src/biocurator/providers/__init__.py` and add an import line:

```python
# src/biocurator/providers/__init__.py
from biocurator.providers.base import DatabaseConfig, DatabaseSearcher, SearchCriteria
from biocurator.providers.registry import ProviderRegistry

import biocurator.providers.ncbi      # registers "ncbi"
import biocurator.providers.uniprot   # registers "uniprot"
import biocurator.providers.ensembl   # registers "ensembl"   ← add this

__all__ = ["DatabaseConfig", "DatabaseSearcher", "SearchCriteria", "ProviderRegistry"]
```

The import triggers the `ProviderRegistry.register()` call at the bottom of your file, so the provider is available whenever `biocurator.providers` is imported.

---

## 5 — Add it to a config

```yaml
# config.yaml
email: your@email.com

databases:
  ensembl:
    name: Ensembl
    base_url: https://rest.ensembl.org
    rate_limit: 0.5
    batch_size: 10

jobs:
  human-genes:
    search:
      databases: [ensembl]
      organism: "homo_sapiens"
      keywords: ["BRCA1"]
      max_results: 20
    filter:
      min_length: 100
    export:
      outdir: results/ensembl
      formats: [fasta, csv]
      prefix: brca1
```

---

## 6 — Write tests

Create `tests/providers/test_ensembl.py`. Follow the same pattern used for the built-in providers:

```python
import pytest
from biocurator.providers.base import SearchCriteria, DatabaseConfig
from biocurator.providers.ensembl import EnsemblSearcher
from biocurator.providers.registry import ProviderRegistry


@pytest.fixture
def config():
    return DatabaseConfig(name="Ensembl", rate_limit=0.0, batch_size=10)


@pytest.fixture
def searcher(config):
    return EnsemblSearcher(config, "test@example.com")


def test_ensembl_registered():
    assert "ensembl" in ProviderRegistry.available()


def test_build_query_organism(searcher):
    criteria = SearchCriteria(organism="homo_sapiens")
    query = searcher.build_query(criteria)
    assert "species:homo_sapiens" in query


def test_build_query_keywords(searcher):
    criteria = SearchCriteria(keywords=["BRCA1", "TP53"])
    query = searcher.build_query(criteria)
    assert "BRCA1" in query
    assert "TP53" in query


def test_build_query_empty_criteria(searcher):
    assert searcher.build_query(SearchCriteria()) == ""
```

Run:

```bash
uv run pytest tests/providers/test_ensembl.py -v
```

---

## 7 — Checklist before submitting

- [ ] `src/biocurator/providers/<name>.py` created
- [ ] All four abstract methods implemented: `build_query`, `search`, `fetch_metadata`, `download`
- [ ] `ProviderRegistry.register("<name>", YourSearcher)` at the bottom of the file
- [ ] Import line added to `src/biocurator/providers/__init__.py`
- [ ] `tests/providers/test_<name>.py` written and passing
- [ ] `uv run pytest` — full suite green

---

Next: [[Python API]]
