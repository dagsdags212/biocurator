<!-- generated-by: gsd-doc-writer -->
# Testing Guide

## Setup

```bash
uv pip install -e .
uv run pytest tests/ -v    # run full suite
make test                  # equivalent shorthand
```

## Test Structure

`tests/` mirrors `src/biocurator/`:

```
tests/
├── conftest.py            # shared fixtures (GlobalConfig, JobConfig, etc.)
├── test_exceptions.py
├── cli/                   # CLI command tests
├── config/                # ConfigLoader tests
├── core/                  # curator, filters, exporter, verifier tests
├── fixtures/              # reusable test data
├── providers/
│   ├── ncbi/              # NCBISearcher, query_builders tests
│   └── uniprot/           # UniProtSearcher tests
└── utils/                 # logging, retry tests
```

## Running Tests

```bash
uv run pytest tests/ -v                              # all tests
uv run pytest tests/core/ -v                         # one directory
uv run pytest tests/core/test_curator.py -v          # one file
uv run pytest -k "test_filter" -v                    # by name pattern
uv run pytest tests/ --cov=src/biocurator --cov-report=term-missing  # with coverage
```

## Mocking Providers

**Never make real API calls in tests.** Use `pytest-mock`:

```python
# Mock NCBI Entrez
def test_ncbi_search(mocker, db_config, ncbi_criteria):
    mocker.patch("Bio.Entrez.esearch", return_value={"IdList": ["id1"]})
    mocker.patch("Bio.Entrez.read", return_value={"IdList": ["id1"]})
    searcher = NCBISearcher(config=db_config)
    assert searcher.search(ncbi_criteria) == ["id1"]

# Mock UniProt HTTP
def test_uniprot_search(mocker, db_config, uniprot_criteria):
    mock_resp = mocker.MagicMock()
    mock_resp.text = "P01308\n"
    mock_resp.raise_for_status = mocker.MagicMock()
    mocker.patch.object(requests, "get", return_value=mock_resp)
    searcher = UniProtSearcher(config=db_config)
    assert "P01308" in searcher.search(uniprot_criteria)
```

## Fake Provider Pattern

For pipeline-level tests, register an in-memory fake provider:

```python
class FakeSearcher:
    def search(self, criteria): return ["id1", "id2"]
    def fetch_metadata(self, ids, criteria):
        for i in ids: yield SequenceRecord(id=i, accession=i, database="fake")
    def download(self, ids, outdir, criteria):
        for i in ids: yield SequenceRecord(id=i, accession=i, database="fake",
                                            sequence="ATCG", sequence_length=400)

ProviderRegistry.register("fake", FakeSearcher)
# ... run test ...
ProviderRegistry._registry.pop("fake", None)  # always clean up
```

## Writing New Tests

- File: `tests/<module>/test_<component>.py`
- Function: `def test_<what_it_does>():`
- Use fixtures from `conftest.py` (inject by parameter name)
- Test one behaviour per function; parametrize for multiple inputs
- All provider tests must mock network calls
