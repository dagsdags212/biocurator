# Plan 01-03 Summary: UniProt Searcher Migration to tenacity

## Commit
a7095bd — `feat: migrate NCBI and UniProt searchers from custom retry to tenacity`

## Files Changed
| File | Action |
|------|--------|
| src/biocurator/providers/uniprot/searcher.py | Modified — replaced `@retry` with `Retrying` class via `_make_retryer()`, `search()` raises `DatabaseSearchError` |
| tests/providers/uniprot/test_searcher.py | Modified — added error behavior tests (DatabaseSearchError, 4xx passthrough, generator catch-and-continue) |

## Verification
- `uv run pytest tests/providers/uniprot/test_searcher.py -x` — 11 passed (including 5 new error behavior tests)
- `uv run pytest tests/ -x` — 154 passed
- UniProt `_safe_get()` uses `Retrying(self.session.get, ...)` + `raise_for_status()` inside retry block
- `_make_retryer()` uses `RETRYABLE_PREDICATE` (filters 4xx via `_is_retryable()`)
- 4xx HTTP errors skip retry entirely; 5xx are retried
- `search()` raises `DatabaseSearchError` on all failure paths
- Generators (fetch_metadata, download) continue on batch/single failure

## Notes
- UniProt searcher migration was executed alongside 01-02 in the same commit
- Per-database retry merge in `run_job()` applies to both NCBI and UniProt
