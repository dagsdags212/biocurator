---
plan: 03-01
phase: 03-checksums-manifests
status: completed
completed_at: 2026-05-26
commits:
  - 56a3514  # Task 1: exporter.py SHA-256 hashing and manifest writing (pre-existing)
  - 0f6146e  # Task 2: curator.py wiring (pre-existing)
  - 894a069  # Task 3: unit tests + integration assertions + curator fix
---

# Summary: Plan 03-01 — SHA-256 Checksums and Manifest Generation

## What Was Done

Tasks 1 and 2 were already committed before this agent ran (commits 56a3514 and 0f6146e). This agent executed Task 3 and fixed a latent bug in Task 2's implementation.

### Task 3: Tests Created

**New file: `tests/core/test_exporter.py`** — 8 unit tests

| Test | Requirement | What It Verifies |
|------|-------------|-----------------|
| `test_sha256_fasta_streaming` | DI-01 | Incremental FASTA hash matches `sha256sum` of disk file |
| `test_sha256_csv_streaming` | DI-01 | Incremental CSV hash matches disk file |
| `test_sha256_json_streaming` | DI-01 | Incremental JSON hash matches disk file (includes brackets and separators) |
| `test_manifest_written_to_outdir` | DI-02 | `manifest.json` exists; `manifest_version=="1.0"`, `job_name`, `stats`, `files` keys present |
| `test_sha256sum_companion_file` | DI-02 | `manifest-sha256.txt` uses double-space format; hash is 64 hex chars |
| `test_manifest_contains_config_snapshot` | DI-03 | `manifest["config"]["name"] == "test-job"` |
| `test_no_manifest_when_no_job_name` | Backward compat | No manifest files when `job_name` is absent |
| `test_record_counts_accurate` | DI-03 | `_record_counts["fasta"] == 3` after writing 3 records |

**Updated file: `tests/core/test_streaming_curation.py`**

- Added `import json`
- Added 5 manifest assertions to `test_run_job_streaming`: manifest path existence, `job_name`, `total_records >= 1`, `manifest-sha256.txt` existence, and `"manifest"` / `"manifest_sha256"` keys in the `results` dict

### Bug Fixed in curator.py (Task 2)

The original implementation placed the manifest path existence checks **inside** the `with StreamingExporter(...)` block, before `__exit__` was called. Since `_write_manifest()` runs in `close()` which is triggered by `__exit__`, the manifest files did not exist at the time of the check. The `return` statement was moved outside the `with` block so the existence checks happen after the context manager fully closes.

## Test Results

```
14 passed in 0.37s
  tests/core/test_streaming_curation.py::test_run_job_streaming  PASSED
  tests/core/test_curator.py (5 tests)                           PASSED
  tests/core/test_exporter.py (8 tests)                          PASSED
```

## Requirements Satisfied

| Requirement | Status |
|-------------|--------|
| DI-01: SHA-256 checksum generation during streaming export | Verified by 3 hash-equality tests |
| DI-02: Per-job manifest.json + manifest-sha256.txt companion | Verified by 2 structure/format tests + integration test |
| DI-03: Config snapshot in manifest | Verified by snapshot test + record count accuracy test |

## Files Modified

| File | Change |
|------|--------|
| `tests/core/test_exporter.py` | Created (8 tests) |
| `tests/core/test_streaming_curation.py` | Added `import json` + 5 manifest assertions |
| `src/biocurator/core/curator.py` | Moved manifest path checks outside `with` block |
