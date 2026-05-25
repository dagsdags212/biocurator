---
phase: 03-checksums-manifests
reviewed: 2026-05-26T00:00:00Z
depth: standard
files_reviewed: 7
findings:
  critical: 5
  warning: 5
  info: 3
  total: 13
status: issues_found
---

# Phase 03: Code Review Report

**Reviewed:** 2026-05-26  
**Depth:** standard  
**Files Reviewed:** 7  
**Status:** issues_found

## Scope

- `src/biocurator/core/__init__.py`
- `src/biocurator/core/curator.py`
- `src/biocurator/core/exporter.py`
- `src/biocurator/core/verifier.py`
- `tests/core/test_exporter.py`
- `tests/core/test_streaming_curation.py`
- `tests/core/test_verifier.py`

---

## Critical Issues

### CR-01 — `_hash_state` not reset in `open()` — reuse produces wrong checksums

**File:** `src/biocurator/core/exporter.py` (`open()`)  
**Severity:** Critical  
`_hash_state` is populated in `__init__` but never re-initialized in `open()`. If `StreamingExporter` is reused (explicit second `open()` call, or context manager re-entered), the second session's SHA-256 objects already contain bytes from the first session. Resulting digests are silently wrong; the manifest passes as valid while containing fabricated checksums.

**Fix:** Add `self._hash_state = {fmt: hashlib.sha256() for fmt in self.formats}` at the top of `open()`.

---

### CR-02 — `__exit__` writes manifest unconditionally even after mid-export exception

**File:** `src/biocurator/core/exporter.py` (`__exit__`)  
**Severity:** Critical  
`__exit__` calls `self.close()` unconditionally, which calls `_finalize_checksums()` and `_write_manifest()`. If an exception aborts the export mid-stream, output files are truncated but the manifest is written with a checksum matching the truncated file. `verify_manifest` then passes, falsely asserting integrity on incomplete data.

**Fix:** Guard manifest writing on clean exit only:
```python
def __exit__(self, exc_type, exc_val, exc_tb) -> None:
    if exc_type is not None:
        self._close_handles()   # close file handles, skip manifest
    else:
        self.close()            # finalize checksums + write manifest
    return False
```

---

### CR-03 — `verify_manifest` does not catch `json.JSONDecodeError` — unhandled crash

**File:** `src/biocurator/core/verifier.py` (around the `json.load` call)  
**Severity:** Critical  
`verify_manifest` guards against `FileNotFoundError` via `path.exists()`, but does not catch `json.JSONDecodeError` from `json.load()`. A malformed or truncated manifest (readily produced by CR-02) causes an unhandled exception rather than a structured error report.

**Fix:**
```python
try:
    data = json.load(f)
except json.JSONDecodeError as exc:
    raise ValueError(f"Manifest file is not valid JSON: {manifest_path}") from exc
```

---

### CR-04 — `verify_file` loads entire file into memory — crashes on large FASTA/SRA files

**File:** `src/biocurator/core/verifier.py` (`verify_file`)  
**Severity:** Critical  
`path.read_bytes()` loads the complete file before hashing. The stated use case (whole-genome FASTA, SRA dumps) routinely produces files in the multi-GB range. A 10 GB file on an 8 GB RAM system OOMs the process. This is a correctness/reliability issue for the primary use case.

**Fix:**
```python
def verify_file(path: Path, expected_checksum: str) -> bool:
    sha256 = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            sha256.update(chunk)
    return sha256.hexdigest() == expected_checksum
```

---

### CR-05 — Incremental hash covers formatted strings; verifier hashes raw bytes — encoding mismatch risk

**File:** `src/biocurator/core/exporter.py` (incremental hash), `src/biocurator/core/verifier.py` (`verify_file`)  
**Severity:** Critical  
The incremental hasher calls `data.encode()` (implicit UTF-8) over formatted string content written to file handles. `verify_file` hashes raw bytes read from disk. These match on Linux with the default UTF-8 locale, but diverge silently on systems with non-UTF-8 locales or platforms that translate line endings (`\n` → `\r\n`). All output file handles should explicitly use `encoding="utf-8"` and `newline="\n"` to eliminate the ambiguity.

---

## Warnings

### WR-01 — Missing format guard in `write_fasta` / `write_csv_row` / `write_json_record`

**File:** `src/biocurator/core/exporter.py`  
Calling `write_fasta()` when `"fasta"` was not in `self.formats` raises a cryptic `AttributeError: 'StreamingExporter' object has no attribute '_fasta_handle'`. Should raise `ExportError("Cannot write FASTA: format not configured for this exporter")` instead.

---

### WR-02 — `_write_manifest` likely uses format strings (`"fasta"`) as file paths instead of actual output paths

**File:** `src/biocurator/core/exporter.py` (`_write_manifest`)  
If the manifest `"file"` field contains the format key (`"fasta"`) rather than the actual output path (e.g., `results/biocurator.fasta`), then `verify_manifest` resolves `manifest_path.parent / "fasta"`, which never exists, and silently reports every entry as `"missing"` — passing verification of deleted output files.

**Fix:** Map format keys to actual `Path` objects before building manifest entries:
```python
format_to_path = {fmt: self.outdir / f"{self.prefix}.{fmt}" for fmt in self._checksums}
```

---

### WR-03 — `verify_manifest` returns flat list with no top-level pass/fail — easy to miss `"missing"` entries

**File:** `src/biocurator/core/verifier.py` (`verify_manifest`)  
The return value is a `list[dict]` with mixed `"ok"/"mismatch"/"missing"` statuses. Callers who check only for `"mismatch"` will silently accept deleted output files as verified. A `tuple[bool, list[...]]` return — `(all_passed, per_file_results)` — or a raised exception on any non-`"ok"` entry would make the contract harder to misuse.

---

### WR-04 — Test expects `FileNotFoundError` from `verify_manifest` when manifest is absent

**File:** `tests/core/test_verifier.py`  
`test_verify_invalid_manifest` (or similar) asserts `pytest.raises(FileNotFoundError)` but `verify_manifest` may return `[]` rather than raising. If the function returns rather than raises, this test passes vacuously or fails unexpectedly in CI. Verify the actual contract and align the assertion.

---

### WR-05 — No integration test verifies that a completed job produces a manifest with correct checksums

**File:** `tests/core/test_streaming_curation.py`  
The streaming curation integration tests confirm that output files are created, but no test asserts that the manifest file exists after `run_job()` and that its checksums match the on-disk output files via `verify_manifest`. The core deliverable of phase 03 — end-to-end checksum verification — has no integration test coverage.

---

## Info

### IN-01 — `verify_file`, `verify_manifest`, `ManifestWriter` not exported from `core/__init__.py`

**File:** `src/biocurator/core/__init__.py`  
Per project conventions, subpackages export public API via `__all__`. `verifier.py`'s public symbols are absent from `__init__.py`, so `from biocurator.core import verify_manifest` raises `ImportError` for any CLI command added in phase 04.

---

### IN-02 — Format strings (`"fasta"`, `"csv"`, `"json"`) are magic literals in 3+ files

An `ExportFormat(str, Enum)` defined once and imported everywhere would eliminate silent typo bugs (e.g., `"Fasta"` silently missing in a dict lookup).

---

### IN-03 — `verify_file` returns `bool` — callers cannot get actual digest without re-reading the file

**File:** `src/biocurator/core/verifier.py` (`verify_file`)  
`verify_manifest` needs the actual digest for mismatch reporting, but `verify_file` only returns `True/False`. Either the file is read twice (once for match, once for digest), or the `"actual"` field in mismatch results is `None`. Changing the signature to `tuple[bool, str]` avoids the double read.

---

_Reviewed: 2026-05-26 | Reviewer: gsd-code-reviewer | Depth: standard_
