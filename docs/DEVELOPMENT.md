<!-- generated-by: gsd-doc-writer -->
# Development Guide

## Setup

```bash
git clone https://github.com/dagsdags212/biocurator.git
cd biocurator
uv pip install -e .        # editable install
uv run pytest tests/ -v    # verify all tests pass
```

## Project Structure

```
src/biocurator/
├── cli/          # Typer CLI — main.py + commands/
├── config/       # YAML config: schema.py (dataclasses), loader.py
├── core/         # curator.py, filters.py, exporter.py, verifier.py
├── providers/    # base.py, registry.py, health.py, ncbi/, uniprot/
├── utils/        # logging.py, retryable_exceptions.py
└── exceptions.py

tests/            # mirrors src/biocurator/ layout
docs/             # canonical documentation
wiki/             # GitHub wiki pages
```

## Make Targets

| Command | Action |
|---------|--------|
| `make test` | Run `uv run pytest tests/` |
| `make build` | Run `uv build` |
| `make install` | Install from GitHub via `uv pip install git+...` |

## Code Style

Ruff is configured in `pyproject.toml` — run before every commit:

```bash
uv run ruff check src/ tests/   # lint
uv run ruff format src/ tests/  # format
```

## Conventions

| Category | Convention | Example |
|----------|-----------|---------|
| Classes | `PascalCase` | `NCBISearcher`, `SequenceFilter` |
| Functions / variables | `snake_case` | `run_job`, `filtered_ids` |
| Constants | `UPPER_SNAKE_CASE` | `_BUILDER_MAP` |
| Test functions | `test_<description>` | `test_filter_rejects_short_sequence` |
| Commit prefixes | `feat:`, `fix:`, `test:`, `docs:`, `refactor:`, `build:`, `chore:` | |

## Adding a New Database Provider

1. **Create criteria class** — extend `SearchCriteria` in `providers/<name>/criteria.py`.
2. **Create searcher** — extend `DatabaseSearcher[YourCriteria]` in `providers/<name>/searcher.py`. Implement `build_query`, `search`, `fetch_metadata`, `download`.
3. **Self-register at module level:**
   ```python
   ProviderRegistry.register("mydb", MySearcher)
   ```
4. **Export from `providers/<name>/__init__.py`**.
5. **Add tests** in `tests/providers/<name>/`.

The `Biocurator` class automatically discovers the provider when a job lists `"mydb"` in `search.databases`.

## Adding a New CLI Command

1. Create `src/biocurator/cli/commands/<name>.py` with a `<name>_command()` function decorated for Typer.
2. Register it in `cli/main.py`: `app.command("<name>")(<name>_command)`.
3. Add tests in `tests/cli/test_<name>.py`.

## Error Handling

- Raise specific exceptions from `exceptions.py` (never raw `Exception`).
- Chain with `from exc` when re-raising.
- Per-record failures: log as `logger.warning(...)` and continue — never abort the batch.

## Logging

```python
logger = get_logger(__name__)
logger.debug(...)    # detailed tracing
logger.info(...)     # lifecycle events
logger.warning(...)  # recoverable errors
logger.error(...)    # non-recoverable errors
```
