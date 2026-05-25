---
plan: 03-02
phase: 03-checksums-manifests
status: complete
completed_at: "2026-05-26"
commits:
  - sha: 6623df6
    message: "feat(03-checksums-manifests): add manifest_verify() library function in core/verifier.py"
  - sha: 60974fb
    message: "test(03-checksums-manifests): add 6 unit tests for manifest_verify() and export public API"
tests_added: 6
tests_passing: 6
---

# Plan 03-02 Summary: manifest_verify() Library Function

## What Was Done

### Task 1: `src/biocurator/core/verifier.py` (NEW)

Created the standalone `manifest_verify(manifest_path: Path) -> dict[str, Any]` library function implementing D-01 of the phase requirements.

**Key implementation details:**

- Pure function — no class, no side effects, no file writes, importable standalone
- Reads `manifest.json` via `json.loads(manifest_path.read_text())`, catches `(json.JSONDecodeError, OSError)` and returns `manifest_valid: False` on failure
- Resolves file paths relative to the manifest directory (`base_dir = manifest_path.parent`)
- Security gate: rejects path entries containing `..` or starting with `/` — skips with `logger.warning`
- Recomputes SHA-256 from disk using chunked 8192-byte reads (`hashlib.sha256()` + `iter(lambda: fh.read(8192), b"")`)
- Returns 7-key aggregate report: `manifest_path`, `manifest_valid`, `files_checked`, `files_matched`, `files_missing`, `files_corrupted`, `results`
- Per-file result entries: `{path, sha256_expected, sha256_actual, status}` where `status` is one of `ok`, `corrupted`, `missing`
- Uses `biocurator.utils.logging.get_logger` logger pattern; all stdlib (no new dependencies)

### Task 2: `tests/core/test_verifier.py` (NEW) + `src/biocurator/core/__init__.py` (UPDATED)

Created 6 unit tests covering all verification outcomes:

| Test | Scenario | Assertion |
|------|----------|-----------|
| `test_verify_all_match` | File on disk matches manifest SHA-256 | `files_matched==1`, `status=="ok"` |
| `test_verify_corrupted_detected` | File changed after manifest written | `files_corrupted==1`, `status=="corrupted"` |
| `test_verify_file_missing` | Referenced file absent from disk | `files_missing==1`, `status=="missing"` |
| `test_verify_invalid_manifest` | Malformed JSON in manifest file | `manifest_valid is False`, `files_checked==0` |
| `test_verify_path_traversal_rejected` | `../etc/passwd` path entry | `files_checked==0` (skipped) |
| `test_verify_mixed_results` | 2 files: 1 ok + 1 corrupted | `files_checked==2`, correct per-file statuses |

Updated `src/biocurator/core/__init__.py` to export `manifest_verify` via `__all__`, enabling `from biocurator.core import manifest_verify`.

## Verification Results

```
tests/core/test_verifier.py::test_verify_all_match PASSED
tests/core/test_verifier.py::test_verify_corrupted_detected PASSED
tests/core/test_verifier.py::test_verify_file_missing PASSED
tests/core/test_verifier.py::test_verify_invalid_manifest PASSED
tests/core/test_verifier.py::test_verify_path_traversal_rejected PASSED
tests/core/test_verifier.py::test_verify_mixed_results PASSED

6/6 passed
```

Full phase suite: **20/20 passed** (test_verifier.py + test_exporter.py + test_streaming_curation.py + test_curator.py)

## Files Modified

- `src/biocurator/core/verifier.py` — CREATED (118 lines)
- `tests/core/test_verifier.py` — CREATED (136 lines)
- `src/biocurator/core/__init__.py` — UPDATED (5 lines, was empty)

## Success Criteria Checklist

- [x] `manifest_verify()` accepts a Path to manifest.json and returns a structured comparison report
- [x] All-match case: report shows all "ok" with matched == checked
- [x] Corrupted case: report shows "corrupted" for modified files
- [x] Missing case: report shows "missing" for absent files
- [x] Invalid manifest: returns `manifest_valid: false`
- [x] Path traversal attempts rejected and skipped
- [x] Pure library function — no CLI, no side effects, importable from `biocurator.core`
- [x] All 6 tests pass
- [x] No modifications to STATE.md or ROADMAP.md
