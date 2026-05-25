---
plan: "04-03"
phase: "04"
status: complete
completed: "2026-05-26"
commits:
  - 330bb86
  - 223a1a3
key_files:
  modified:
    - src/biocurator/cli/commands/files.py
    - tests/cli/test_files.py
requirements_addressed:
  - CLI-03
---

# Plan 04-03 Summary: biocurator files --verify mode

## What Was Built

Extended `files_command` to implement real SHA-256 checksum verification via the existing `manifest_verify()` library function. When `--verify` is passed:

- **Single-job mode** (`biocurator files alpha-job --verify`): Calls `manifest_verify(manifest_path)`, renders a per-file status table (✓ ok / ✗ corrupted / ? missing), exits 1 if any file is corrupted or missing.
- **All-jobs mode** (`biocurator files --verify`): Iterates all jobs with manifests, runs verify on each, reports aggregate result. Exits 1 if any job has failures.
- **No manifest**: exits 0 with hint to run the job first.

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| 04-03-01 | Replace verify stub with manifest_verify implementation | 330bb86 |
| 04-03-02 | Add 4 verify-mode tests to test_files.py | 223a1a3 |

## Verification

```
uv run pytest tests/cli/test_files.py -q
# → 9 passed (5 list-mode + 4 verify-mode)
uv run pytest tests/ -q
# → 182 passed
```

## Deviations

Minor fix: initial implementation did not propagate `_verify_one_job()` return value in the single-job path. Fixed before final commit.

## Self-Check: PASSED

- files.py imports manifest_verify from biocurator.core: CONFIRMED
- verify stub replaced: CONFIRMED (no "not yet implemented" text)
- result["all_ok"] branch prints "All checksums verified": CONFIRMED
- Exit 1 on files_corrupted > 0: CONFIRMED
- Exit 1 on files_missing > 0: CONFIRMED
- pytest tests/cli/test_files.py: 9 passed
- pytest tests/ (full suite): 182 passed
