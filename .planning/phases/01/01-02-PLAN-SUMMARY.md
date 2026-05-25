# Plan 01-02 Summary: NCBI Searcher Migration to tenacity

## Commit
a7095bd — `feat: migrate NCBI and UniProt searchers from custom retry to tenacity`

## Files Changed
| File | Action |
|------|--------|
| src/biocurator/providers/ncbi/searcher.py | Modified — replaced `@retry` with `Retrying` class, split parse from network, `search()` raises `DatabaseSearchError`, added `_fetch_single()` |
| src/biocurator/core/curator.py | Modified — added `global_retry` param, retry config merge in `run_job()` |
| src/biocurator/cli/commands/run.py | Modified — passes `global_config.retry` to Biocurator |
| src/biocurator/utils/retryable_exceptions.py | Modified — replaced type-based predicate with `_is_retryable()` custom function filtering 4xx errors |
| tests/providers/ncbi/test_searcher.py | Modified — added error behavior tests (DatabaseSearchError, generator catch-and-continue) |
| tests/utils/test_network.py | Modified — replaced old `@retry` tests with retryable exception classification tests |

## Verification
- `uv run pytest tests/providers/ncbi/test_searcher.py -x` — 15 passed (including 5 new error behavior tests)
- `uv run pytest tests/utils/test_network.py -x` — 11 passed (retryable classification)
- `uv run pytest tests/ -x` — 154 passed
- NCBI `_safe_entrez_call` uses `Retrying(func, **kwargs)` + `Entrez.read(handle)` outside retry
- `_make_retryer()` builds `Retrying` with `RETRYABLE_PREDICATE` (filters 4xx), `stop_after_attempt`, `wait_exponential`, `before_sleep_log`
- Retry merge: per-database override > global retry > tenacity defaults, applied in `run_job()` loop
- `search()` now raises `DatabaseSearchError` on all failure paths

## Notes
- `preview.py` had auto-formatting changes (ruff), included in commit
- Phase 1 is functionally complete — all 3 plans executed and committed
