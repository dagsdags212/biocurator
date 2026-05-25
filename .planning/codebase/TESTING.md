# Testing Patterns

**Analysis Date:** 2026-05-25

## Test Framework

**Runner:**
- pytest 8.4+ (local) / 9.0.3 (seen in `.pyc` footprints)
- Config: `pyproject.toml` under `[dependency-groups] dev` — `pytest>=8.0`, `pytest-mock>=3.0`
- No `pytest.ini`, `pytest.toml`, `conftest.py`, or custom pytest config found

**Assertion Library:**
- Plain `assert` statements — no `self.assert*` or `unittest.TestCase` usage
- `pytest.raises()` for exception testing
- `unittest.mock.MagicMock` for mock objects

**Run Commands:**
```bash
uv run pytest                         # Run all tests
uv run pytest -v --tb=short           # Verbose with short traceback (CI mode)
uv run pytest tests/path/to/test.py   # Single test file
make test                             # Makefile alias for `uv run pytest tests`
```

---

## Test File Organization

**Structure:** Tests mirror the `src/biocurator/` source tree exactly.

```
tests/
├── __init__.py
├── test_exceptions.py                    # → src/biocurator/exceptions.py
├── fixtures/                             # Test data (YAML files)
│   ├── valid_config.yaml
│   ├── missing_email.yaml
│   └── missing_databases.yaml
├── config/
│   ├── __init__.py
│   ├── test_loader.py                    # → src/biocurator/config/loader.py
│   └── test_schema.py                   # → src/biocurator/config/schema.py
├── core/
│   ├── __init__.py
│   ├── test_curator.py                  # → src/biocurator/core/curator.py
│   └── test_streaming_curation.py       # Stream export → exporter.py
├── providers/
│   ├── __init__.py
│   ├── test_base.py                     # → src/biocurator/providers/base.py
│   ├── test_registry.py                 # → src/biocurator/providers/registry.py
│   ├── test_sequence_record.py          # → SequenceRecord dataclass
│   ├── ncbi/
│   │   ├── __init__.py
│   │   ├── test_apikey.py
│   │   ├── test_criteria.py             # → NCBISearchCriteria
│   │   ├── test_query_builders.py       # → All NCBI query builders
│   │   └── test_searcher.py             # → NCBISearcher
│   └── uniprot/
│       ├── __init__.py
│       ├── test_criteria.py             # → UniProtSearchCriteria
│       ├── test_query_builders.py       # → UniProtQueryBuilder
│       └── test_searcher.py             # → UniProtSearcher
├── cli/
│   ├── __init__.py
│   ├── test_init.py                     # → cli/commands/init.py
│   └── test_run.py                      # → cli/commands/run.py
└── utils/
    ├── __init__.py
    ├── test_logging.py                  # → utils/logging.py
    └── test_network.py                  # → utils/network.py
```

**Naming convention:** `test_<module_name>.py` for each source module.

**File naming test → source mapping:**
- `src/biocurator/config/loader.py` → `tests/config/test_loader.py`
- `src/biocurator/providers/ncbi/query_builders.py` → `tests/providers/ncbi/test_query_builders.py`

---

## Test Coverage by Module

| Module | Test File | Test Count | What's Tested |
|--------|-----------|-----------|---------------|
| `exceptions.py` | `test_exceptions.py` | 3 | All 6 exception classes are BiocuratorError subclasses, message carry, catchable as base |
| `config/schema.py` | `test_schema.py` | 6 | Defaults for all config dataclasses, full job config assembly |
| `config/loader.py` | `test_loader.py` | 7 | Valid config loading, missing file, missing email, missing databases, empty sections, defaults |
| `providers/base.py` | `test_base.py` | 8 | SearchCriteria defaults/fields, DatabaseConfig, DatabaseSearcher ABC enforcement |
| `providers/registry.py` | `test_registry.py` | 7 | Registration, retrieval, overwrite, error handling, config/email forwarding |
| `providers/ncbi/criteria.py` | `test_criteria.py` | 6 | Subclass check, default database, field setting, inheritance |
| `providers/ncbi/query_builders.py` | `test_query_builders.py` | 19 | All 5 query builders — per-builder tests for organism, keywords, length, dates, exclude, factory |
| `providers/ncbi/searcher.py` | `test_searcher.py` | 10 | Registration check, build_query delegation to builder, query construction combinations |
| `providers/ncbi/searcher.py` | `test_apikey.py` | 2 | API key forwarding to Bio.Entrez |
| `providers/uniprot/criteria.py` | `test_criteria.py` | 5 | Subclass check, reviewed default/true/false, inheritance |
| `providers/uniprot/query_builders.py` | `test_query_builders.py` | 11 | All builder methods — organism, keywords, length, reviewed, combined, available_fields |
| `providers/uniprot/searcher.py` | `test_searcher.py` | 6 | Registration check, build_query combinations |
| `core/curator.py` | `test_curator.py` | 5 | search/download calls, length filter, fasta export, progress callback, unknown DB |
| `core/exporter.py` | `test_streaming_curation.py` | 1 | Full streaming pipeline produces correct FASTA/CSV/JSON output |
| `cli/commands/init.py` | `test_init.py` | 4 | stdout printing, file writing, advanced template, basic template |
| `cli/commands/run.py` | `test_run.py` | 5 | Missing config, dry-run, job execution, job filtering, unknown job name |
| `utils/logging.py` | `test_logging.py` | 3 | `@log_function_call` preserves name, docstring, and calls function |
| `utils/network.py` | `test_network.py` | 4 | Retry success, eventual success, max attempts, unhandled exception |
| `providers/base.py` | `test_sequence_record.py` | 3 | Required fields, optional defaults, sequence data |

**Total:** ~100 test functions across 18 test files (4,198 lines of test code vs 7,480 lines of source code).

---

## Fixture Usage

No `conftest.py` file exists. Fixtures are defined **inline within test files**.

**Common fixture patterns:**

```python
# Configuration fixture (test_providers/ncbi/test_searcher.py)
@pytest.fixture
def config():
    return DatabaseConfig(name="NCBI", rate_limit=0.0, batch_size=20)

@pytest.fixture
def searcher(config):
    return NCBISearcher(config, "test@example.com")
```

```python
# Job config fixture (test_core/test_curator.py)
@pytest.fixture
def job_config(tmp_path):
    return JobConfig(
        name="test-job",
        search=SearchConfig(databases=["ncbi"], organism="E. coli", max_results=5),
        filter=FilterConfig(min_length=100),
        export=ExportConfig(outdir=str(tmp_path / "results"), formats=["fasta"]),
    )
```

```python
# Mock searcher fixture (test_core/test_curator.py)
@pytest.fixture
def mock_ncbi_searcher():
    searcher = MagicMock()
    searcher.search.return_value = ["123", "456"]
    searcher.fetch_metadata.return_value = iter([...])
    searcher.download.return_value = iter([...])
    return searcher
```

```python
# Registry isolation fixture (test_providers/test_registry.py)
@pytest.fixture(autouse=True)
def clean_registry():
    """Isolate registry state between tests."""
    original = dict(ProviderRegistry._registry)
    yield
    ProviderRegistry._registry.clear()
    ProviderRegistry._registry.update(original)
```

**Built-in fixtures used:**
- `tmp_path` — for temporary directories (output, config files)
- `pytest.raises` — context manager for expected exceptions

---

## Mocking Patterns

**Framework:** `unittest.mock` (`MagicMock`, `patch`) — no mocks from pytest-mock (`mocker`).

**`MagicMock` for full object stubs:**
```python
searcher = MagicMock()
searcher.search.return_value = ["123", "456"]
searcher.fetch_metadata.return_value = iter([record1, record2])
searcher.download.return_value = iter([record1])
curator.searchers["ncbi"] = searcher
```

**`patch` for module-level mocking:**
```python
from unittest.mock import patch

# Patch a class constructor
with patch("biocurator.cli.commands.run.Biocurator") as mock_cls:
    mock_instance = MagicMock()
    mock_instance.run_job.return_value = {"fasta": tmp_path / "out.fasta"}
    mock_cls.return_value = mock_instance
    result = runner.invoke(app, ["run", str(cfg)])

# Patch a function import
with patch("biocurator.providers.ncbi.searcher.get_builder", return_value=mock_builder) as mock_get:
    result = searcher.build_query(criteria)
    mock_get.assert_called_once_with(...)

# Patch a module attribute
with patch.object(Entrez, "api_key", None, create=True):
    NCBISearcher(config, "test@example.com")
```

**What's mocked vs what's real:**
- **Mocked:** External services (NCBI Entrez API, UniProt REST API), CLI app class (`Biocurator`), QueryBuilder instances
- **Real:** Config parsing, schema dataclasses, SearchCriteria, query builder logic, logging utilities, retry decorator logic, exception classes
- **No mocking of:** File I/O (uses `tmp_path` with real file writes), `SequenceRecord` dataclass, `StreamingExporter`

---

## CLI Testing

**Framework:** `typer.testing.CliRunner`

```python
from typer.testing import CliRunner
from biocurator.cli.main import app

runner = CliRunner()

def test_init_prints_to_stdout_by_default():
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    assert "email:" in result.output
```

CLI tests verify exit codes, output content, and file creation. `Biocurator` class is mocked in `test_run.py` to avoid actual database calls.

---

## Test Fixtures (Data)

Test fixture YAML files in `tests/fixtures/`:
- `valid_config.yaml` — full 2-job config with all fields populated
- `missing_email.yaml` — config missing `email` field
- `missing_databases.yaml` — config missing `databases` under search

These are loaded via `Path(__file__).parent.parent / "fixtures"`:

```python
FIXTURES = Path(__file__).parent.parent / "fixtures"

def test_load_valid_config():
    cfg = ConfigLoader.load(FIXTURES / "valid_config.yaml")
```

Inline YAML strings are also used via `tmp_path` for dynamic config generation in CLI tests.

---

## Parameterized Testing

**Not used.** There are no `@pytest.mark.parametrize` decorators anywhere in the test suite. Instead, each variation gets its own test function (e.g., separate `test_builder_organism`, `test_builder_keywords`, `test_builder_length_min` etc. instead of parametrized).

---

## Test Types

### Unit Tests (majority)
- Schema defaults and field validation
- Query builder string construction for every builder/database combination
- SearchCriteria field defaults and inheritance
- Exception hierarchy checks
- Registry registration/lookup logic
- `@log_function_call` decorator behavior
- `@retry` decorator behavior (success, retry, max attempts, unhandled exceptions)
- API key forwarding to Entrez
- `SequenceRecord` dataclass construction

### Integration Tests (some)
- ConfigLoader with real YAML files from `tests/fixtures/`
- StreamingExporter with real file I/O via `tmp_path` (`test_streaming_curation.py`)
- CLI command integration via `CliRunner`
- `NCBISearcher.build_query()` — real delegation to builder (no mock for builder itself in `test_searcher.py`)
- `ProviderRegistry` with real searcher classes

### What's NOT tested
- **Actual network calls** — all external API calls (NCBI Entrez, UniProt REST) are mocked or avoided
- **`SequenceFilter`** — the entire `src/biocurator/core/filters.py` (324 lines) has NO dedicated test file or tests
- **`StreamingExporter` standalone** — only tested indirectly through `test_streaming_curation.py` which tests it via `Biocurator.run_job()`
- **`preview_command`** — no test file exists for `cli/commands/preview.py`
- **Error paths in searchers** — no tests that `search()` or `fetch_metadata()` raise/handle exceptions

---

## Notable Gaps

| Area | Missing Coverage | Risk |
|------|-----------------|------|
| `core/filters.py` (324 lines) | Zero tests — quality scoring, duplicate removal, taxonomy filter, date filter | Untested core filtering logic ranked HIGH |
| `providers/ncbi/searcher.py` `_safe_entrez_call`, `search`, `fetch_metadata`, `download` | Only `build_query` tested; streaming/retry/error paths untested | HIGH — core data access layer |
| `providers/uniprot/searcher.py` | Only `build_query` tested; `search`, `fetch_metadata`, `download` untested | HIGH — core data access layer |
| `cli/commands/preview.py` | No test file | MEDIUM — CLI preview command |
| `core/exporter.py` `StreamingExporter` | Only tested via `curator.run_job()` integration; no unit tests for `open`, `write_record`, `close` | MEDIUM |
| Error recovery paths | No tests for exception handling in searcher `search()`/`fetch_metadata()`/`download()` | MEDIUM |

---

## CI Test Configuration

**File:** `.github/workflows/ci.yml`

```yaml
- name: Run tests
  run: uv run pytest -v --tb=short
```

**CI Details:**
- Python 3.13 only (single matrix)
- `ubuntu-latest` runner
- `astral-sh/setup-uv@v6` with cache
- `uv sync --frozen` for dependencies
- No coverage collection configured
- Runs on push/PR to `main`
- Publish workflow runs tests before deploying

**No coverage requirements enforced** — no `--cov` flag, no coverage config, no `coverage` dependency in dev group.

---

*Testing analysis: 2026-05-25*
