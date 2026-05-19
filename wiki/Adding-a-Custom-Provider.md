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
# 134 passed
```

---

## 2 — How providers work

biocurator uses a **provider registry** to decouple database logic from the pipeline. Each provider is a self-contained Python subpackage under `src/biocurator/providers/` that:

1. Defines a **criteria class** (`SearchCriteria` subclass) with any database-specific parameters
2. Implements a **`QueryBuilder`** that translates criteria into a query string for that database's API
3. Implements a **`DatabaseSearcher`** with four methods: `build_query`, `search`, `fetch_metadata`, `download`
4. Calls `ProviderRegistry.register()` at import time to make itself available by name

When the pipeline initialises, it calls `ProviderRegistry.get("ensembl", config, email)` — it never imports a concrete class directly. Adding a new database requires **one new subpackage** and no changes to the pipeline.

### Key classes

| Class | Module | Role |
|-------|--------|------|
| `SearchCriteria` | `biocurator.providers.base` | Base class for structured search parameters — subclass this |
| `QueryBuilder[T]` | `biocurator.providers.base` | Generic ABC for building query strings — subclass this |
| `DatabaseSearcher[C]` | `biocurator.providers.base` | Generic ABC for provider logic — subclass this |
| `DatabaseConfig` | `biocurator.providers.base` | Connection settings (URL, rate limit, batch size, …) |
| `SequenceRecord` | `biocurator.providers.base` | Typed return value for `fetch_metadata` and `download` |
| `ProviderRegistry` | `biocurator.providers.registry` | Global name → class map; call `register()` and `get()` |

### `SearchCriteria` base fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `organism` | `str \| None` | `None` | Taxonomic name |
| `keywords` | `list[str]` | `[]` | Free-text keywords |
| `min_length` | `int \| None` | `None` | Minimum sequence length |
| `max_length` | `int \| None` | `None` | Maximum sequence length |
| `start_date` | `str \| None` | `None` | Earliest submission date |
| `end_date` | `str \| None` | `None` | Latest submission date |
| `max_results` | `int` | `100` | Upper bound on returned IDs |
| `exclude_terms` | `list[str]` | `[]` | Terms that must not appear |
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

### `SequenceRecord` fields

`fetch_metadata` and `download` return `list[SequenceRecord]`. Populate at minimum:

| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | Used to look up records for download |
| `accession` | `str` | Written to FASTA headers and CSV |
| `database` | `str` | Appears in summary reports |
| `organism` | `str` | Used by organism-based filters |
| `sequence_length` | `int` | Used by length filters |
| `sequence` | `str \| None` | Set by `download`; `None` in metadata-only records |
| `downloaded` | `bool` | Set to `True` in `download` |

---

## 3 — Create the subpackage

Providers live in `src/biocurator/providers/<name>/`. Create the directory and four files:

```
src/biocurator/providers/ensembl/
├── __init__.py
├── criteria.py
├── query_builders.py
└── searcher.py
```

### `criteria.py`

Define any parameters the database needs beyond the base `SearchCriteria`:

```python
# src/biocurator/providers/ensembl/criteria.py
from dataclasses import dataclass
from biocurator.providers.base import SearchCriteria


@dataclass
class EnsemblSearchCriteria(SearchCriteria):
    species: str = "homo_sapiens"   # Ensembl uses a separate species field
    feature_type: str | None = None  # e.g. "gene", "transcript"
```

### `query_builders.py`

Implement `QueryBuilder[EnsemblSearchCriteria]`:

```python
# src/biocurator/providers/ensembl/query_builders.py
from biocurator.providers.base import QueryBuilder
from biocurator.providers.ensembl.criteria import EnsemblSearchCriteria


class EnsemblQueryBuilder(QueryBuilder[EnsemblSearchCriteria]):
    def build(self, criteria: EnsemblSearchCriteria) -> str:
        parts = []
        if criteria.keywords:
            parts.append(" OR ".join(criteria.keywords))
        if criteria.feature_type:
            parts.append(f"feature:{criteria.feature_type}")
        return " AND ".join(parts)

    def available_fields(self) -> dict[str, str]:
        return {
            "id": "Ensembl stable ID",
            "symbol": "Gene symbol",
            "description": "Gene description",
            "species": "Species name (Ensembl format, e.g. homo_sapiens)",
            "feature_type": "Feature type: gene, transcript, exon",
            "biotype": "Biotype, e.g. protein_coding",
        }
```

### `searcher.py`

Implement `DatabaseSearcher[EnsemblSearchCriteria]` and register the provider:

```python
# src/biocurator/providers/ensembl/searcher.py
import time
from pathlib import Path

import requests

from biocurator.providers.base import DatabaseConfig, DatabaseSearcher, SequenceRecord
from biocurator.providers.ensembl.criteria import EnsemblSearchCriteria
from biocurator.providers.ensembl.query_builders import EnsemblQueryBuilder
from biocurator.providers.registry import ProviderRegistry
from biocurator.utils.logging import get_logger

logger = get_logger(__name__)


class EnsemblSearcher(DatabaseSearcher[EnsemblSearchCriteria]):
    def __init__(self, config: DatabaseConfig, email: str) -> None:
        super().__init__(config, email)
        self._base_url = config.base_url or "https://rest.ensembl.org"
        self._session = requests.Session()
        self._session.headers["Content-Type"] = "application/json"

    def build_query(self, criteria: EnsemblSearchCriteria) -> str:
        return EnsemblQueryBuilder().build(criteria)

    def search(self, criteria: EnsemblSearchCriteria) -> list[str]:
        logger.info("Searching Ensembl...")
        query = self.build_query(criteria)
        try:
            response = self._session.get(
                f"{self._base_url}/lookup/symbol/{criteria.species}/{query}",
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

    def fetch_metadata(
        self, ids: list[str], criteria: EnsemblSearchCriteria | None = None
    ) -> list[SequenceRecord]:
        logger.info(f"Fetching metadata for {len(ids)} Ensembl IDs...")
        results = []
        for ensembl_id in ids:
            try:
                response = self._session.get(
                    f"{self._base_url}/lookup/id/{ensembl_id}",
                    timeout=self.config.timeout,
                )
                response.raise_for_status()
                entry = response.json()
                results.append(SequenceRecord(
                    id=ensembl_id,
                    accession=ensembl_id,
                    title=entry.get("display_name", ""),
                    organism=entry.get("species", ""),
                    sequence_length=entry.get("end", 0) - entry.get("start", 0),
                    database="Ensembl",
                ))
                time.sleep(self.config.rate_limit)
            except Exception as exc:
                logger.warning(f"Could not fetch metadata for {ensembl_id}: {exc}")
        return results

    def download(
        self,
        ids: list[str],
        outdir: Path,
        criteria: EnsemblSearchCriteria | None = None,
    ) -> list[SequenceRecord]:
        logger.info(f"Downloading {len(ids)} Ensembl sequences...")
        downloaded = []
        for ensembl_id in ids:
            try:
                response = self._session.get(
                    f"{self._base_url}/sequence/id/{ensembl_id}",
                    headers={"Content-Type": "text/plain"},
                    timeout=self.config.timeout,
                )
                response.raise_for_status()
                sequence = response.text.strip()
                downloaded.append(SequenceRecord(
                    id=ensembl_id,
                    accession=ensembl_id,
                    sequence=sequence,
                    sequence_length=len(sequence),
                    database="Ensembl",
                    downloaded=True,
                ))
                time.sleep(self.config.rate_limit)
            except Exception as exc:
                logger.warning(f"Could not download {ensembl_id}: {exc}")
        return downloaded


# Self-register — this line is what makes "ensembl" usable by name.
ProviderRegistry.register("ensembl", EnsemblSearcher)
```

### `__init__.py`

Re-export the public symbols so callers can import from `biocurator.providers.ensembl`:

```python
# src/biocurator/providers/ensembl/__init__.py
from biocurator.providers.ensembl.criteria import EnsemblSearchCriteria
from biocurator.providers.ensembl.query_builders import EnsemblQueryBuilder
from biocurator.providers.ensembl.searcher import EnsemblSearcher

__all__ = ["EnsemblQueryBuilder", "EnsemblSearchCriteria", "EnsemblSearcher"]
```

---

## 4 — Register the provider

Open `src/biocurator/providers/__init__.py` and add an import line. The import triggers the `ProviderRegistry.register()` call at the bottom of your `searcher.py`:

```python
# src/biocurator/providers/__init__.py
from biocurator.providers.base import (
    DatabaseConfig, DatabaseSearcher, NCBIDatabase,
    QueryBuilder, SearchCriteria, SequenceRecord,
)
from biocurator.providers.ncbi import NCBISearchCriteria, NCBISearcher, get_builder
from biocurator.providers.registry import ProviderRegistry
from biocurator.providers.uniprot import UniProtQueryBuilder, UniProtSearchCriteria, UniProtSearcher
from biocurator.providers.ensembl import EnsemblSearchCriteria, EnsemblSearcher  # ← add this

__all__ = [
    ...,
    "EnsemblSearchCriteria",
    "EnsemblSearcher",
]
```

---

## 5 — Add it to a config

```yaml
email: your@email.com

jobs:
  human-genes:
    search:
      databases: [ensembl]
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

Mirror the source structure: create `tests/providers/ensembl/` with an `__init__.py` and dedicated test modules.

```
tests/providers/ensembl/
├── __init__.py
├── test_criteria.py
├── test_query_builders.py
└── test_searcher.py
```

**`test_criteria.py`**

```python
from biocurator.providers.base import SearchCriteria
from biocurator.providers.ensembl import EnsemblSearchCriteria


def test_is_search_criteria_subclass():
    assert issubclass(EnsemblSearchCriteria, SearchCriteria)

def test_default_species():
    c = EnsemblSearchCriteria()
    assert c.species == "homo_sapiens"

def test_inherits_base_fields():
    c = EnsemblSearchCriteria(keywords=["BRCA1"], max_results=50)
    assert "BRCA1" in c.keywords
    assert c.max_results == 50
```

**`test_query_builders.py`**

```python
from biocurator.providers.ensembl import EnsemblQueryBuilder, EnsemblSearchCriteria


def test_build_keywords():
    b = EnsemblQueryBuilder()
    q = b.build(EnsemblSearchCriteria(keywords=["BRCA1", "TP53"]))
    assert "BRCA1" in q and "TP53" in q

def test_build_feature_type():
    b = EnsemblQueryBuilder()
    q = b.build(EnsemblSearchCriteria(feature_type="gene"))
    assert "feature:gene" in q

def test_available_fields_returns_dict():
    b = EnsemblQueryBuilder()
    fields = b.available_fields()
    assert isinstance(fields, dict)
    assert "id" in fields
```

**`test_searcher.py`**

```python
import pytest
from biocurator.providers.base import DatabaseConfig
from biocurator.providers.ensembl import EnsemblSearcher, EnsemblSearchCriteria
from biocurator.providers.registry import ProviderRegistry


@pytest.fixture
def config():
    return DatabaseConfig(name="Ensembl", rate_limit=0.0, batch_size=10)

@pytest.fixture
def searcher(config):
    return EnsemblSearcher(config, "test@example.com")

def test_ensembl_registered():
    assert "ensembl" in ProviderRegistry.available()

def test_build_query_keywords(searcher):
    criteria = EnsemblSearchCriteria(keywords=["BRCA1"])
    assert "BRCA1" in searcher.build_query(criteria)

def test_build_query_empty(searcher):
    assert searcher.build_query(EnsemblSearchCriteria()) == ""
```

Run the suite:

```bash
uv run pytest tests/providers/ensembl/ -v
uv run pytest   # full suite — make sure nothing regressed
```

---

## 7 — Checklist before submitting

- [ ] `src/biocurator/providers/<name>/` subpackage created with `__init__.py`, `criteria.py`, `query_builders.py`, `searcher.py`
- [ ] `<Name>SearchCriteria(SearchCriteria)` dataclass defined with any provider-specific fields
- [ ] `<Name>QueryBuilder(QueryBuilder[<Name>SearchCriteria])` implements `build()` and `available_fields()`
- [ ] `<Name>Searcher(DatabaseSearcher[<Name>SearchCriteria])` implements all four abstract methods; `fetch_metadata` and `download` return `list[SequenceRecord]`
- [ ] `ProviderRegistry.register("<name>", <Name>Searcher)` at the bottom of `searcher.py`
- [ ] `__init__.py` re-exports the public symbols
- [ ] Import line added to `src/biocurator/providers/__init__.py`
- [ ] `tests/providers/<name>/` with `__init__.py`, `test_criteria.py`, `test_query_builders.py`, `test_searcher.py`
- [ ] `uv run pytest` — full suite green

---

Next: [[Python API]]
