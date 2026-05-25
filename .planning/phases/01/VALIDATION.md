---
phase: 1
slug: error-handling-retry-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-25
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 |
| **Config file** | pyproject.toml |
| **Quick run command** | `uv run pytest tests/config/test_schema.py tests/config/test_loader.py -x` |
| **Full suite command** | `uv run pytest -x` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/config/test_schema.py tests/config/test_loader.py -x`
- **After Wave 1 complete:** Run `uv run pytest -x`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|--------|
| 1-01-01 | 01-01 | 1 | CFG-01, CFG-02 | T-01-04 | Retry caps prevent infinite retries | unit | `uv run pytest tests/config/test_schema.py -x` | ⬜ |
| 1-01-02 | 01-01 | 1 | CFG-01, CFG-02 | — | Backward compat: existing configs parse without error | unit | `uv run pytest tests/config/test_loader.py -x` | ⬜ |
| 1-01-03 | 01-01 | 1 | ERR-04 | — | RETRYABLE_EXCEPTIONS correctly classified | unit | `python -c "from biocurator.utils.retryable_exceptions import RETRYABLE_EXCEPTIONS; assert len(RETRYABLE_EXCEPTIONS) == 7"` | ⬜ |
| 1-02-01 | 01-02 | 2 | ERR-01, ERR-02, ERR-03 | T-01-05, T-01-06 | NCBI retry uses tenacity, parse outside retry | unit | `uv run pytest tests/providers/ncbi/test_searcher.py -x` | ⬜ |
| 1-02-02 | 01-02 | 2 | ERR-01, ERR-02 | — | Retry merge logic in run_job | unit | `uv run pytest tests/core/ -x 2>/dev/null; python -c "..."` | ⬜ |
| 1-02-03 | 01-02 | 2 | ERR-01, ERR-03 | — | Error behavior tests pass | unit | `uv run pytest tests/utils/test_network.py tests/providers/ncbi/test_searcher.py -x` | ⬜ |
| 1-03-01 | 01-03 | 2 | ERR-01, ERR-02, ERR-03 | T-01-05 | UniProt retry uses tenacity, raise_for_status outside retry | unit | `uv run pytest tests/providers/uniprot/test_searcher.py -x` | ⬜ |
| 1-03-02 | 01-03 | 2 | ERR-01 | — | UniProt error behavior + RetryConfig tests | unit | `uv run pytest tests/providers/uniprot/test_searcher.py tests/config/test_schema.py -x` | ⬜ |

---

## Wave 0 Requirements

- [ ] `tests/config/test_schema.py` — schema tests exist (add RetryConfig tests)
- [ ] `tests/utils/test_network.py` — old retry tests to be replaced
- [ ] Existing infrastructure covers most phase requirements; Wave 0 adds test stubs for new behaviors.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Retry log messages show attempt number | ERR-04 | Requires log capture | Run a searcher test with mock that raises 2x, check logs contain "Retrying" + attempt count |
| CLI error message on failed search | ERR-01 | Integration test | Run `biocurator preview bad_job` with network down, verify DatabaseSearchError shown |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
