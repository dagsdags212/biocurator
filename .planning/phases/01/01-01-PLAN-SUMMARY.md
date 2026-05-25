# Plan 01-01 Summary: Foundation — Config Schema, RetryConfig, Exception Types, tenacity

## Commit
52093ca — `feat(01-01): add RetryConfig, tenacity dep, retryable exceptions, remove custom @retry`

## Files Changed
| File | Action |
|------|--------|
| pyproject.toml | Modified — added tenacity>=9.1,<10.0 |
| src/biocurator/config/schema.py | Modified — added RetryConfig dataclass + retry fields |
| src/biocurator/providers/base.py | Modified — added retry field to DatabaseConfig |
| src/biocurator/config/loader.py | Modified — parse retry blocks from YAML |
| src/biocurator/utils/retryable_exceptions.py | Created — RETRYABLE_EXCEPTIONS tuple + predicate |
| src/biocurator/utils/network.py | Modified — removed custom @retry decorator |

## Verification
- `uv run pytest tests/config/test_schema.py -x` — 6 passed
- `uv run pytest tests/config/test_loader.py -x` — 9 passed
- RetryConfig.resolve(), defaults(), from_dict() verified
- Backward compat: existing configs without retry parse with retry=None
- Import chain: all new modules import cleanly
- Custom @retry raises ImportError as expected

## Notes
- NCBI searcher still imports from biocurator.utils.network — will be fixed in Plan 01-02
- Old test_network.py tests for @retry will fail until Plan 01-02 replaces them
