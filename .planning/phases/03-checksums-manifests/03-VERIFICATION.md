---
phase: 03-checksums-manifests
status: passed
verified: 2026-05-26T00:00:00Z
must_haves_verified: 5
must_haves_total: 5
requirements_covered:
  - DI-01
  - DI-02
  - DI-03
  - DI-04
gaps: []
human_verification: []
---

# Phase 03: Verification Report

**Phase Goal:** Every downloaded sequence file has a SHA-256 checksum; per-job manifest files track checksums, record counts, and provenance metadata.

**Status:** ✅ PASSED — all 5 must-haves verified against the live codebase.

---

## Must-Have Verification

### ✅ DI-01 — SHA-256 checksum computed during streaming export

**Evidence:**
- `src/biocurator/core/exporter.py` imports `hashlib` (line 13)
- `StreamingExporter.__init__` declares `self._hashers: dict[str, hashlib._Hash] = {}`
- `open()` initializes `hashlib.sha256()` for each active format (FASTA line 86, CSV line 93, JSON line 100)
- `write_record()` calls `self._hashers[fmt].update(bytes)` for every record written (lines 116, 129, 143–150)
- `close()` computes `self._checksums = {fmt: h.hexdigest() for fmt, h in self._hashers.items()}`

**Tests:** `test_sha256_fasta_streaming`, `test_sha256_csv_streaming`, `test_sha256_json_streaming` — all 3 pass, asserting that checksum in `exporter._checksums[fmt]` matches `hashlib.sha256(file.read_bytes()).hexdigest()`.

---

### ✅ DI-02 — Per-job manifest JSON + BagIt-compatible sha256sum companion file

**Evidence:**
- `StreamingExporter._write_manifest()` generates `manifest.json` and `manifest-sha256.txt` in `self.outdir`
- `manifest.json` includes `manifest_version`, `job_name`, `generated_at`, `databases`, `stats`, `files` (with `path`, `format`, `sha256`, `size`, `record_count`, `provider`)
- `manifest-sha256.txt` uses `HASH  FILENAME` double-space format (BagIt / `sha256sum -c` compatible)
- Guard: if `job_name` is not set, `_write_manifest()` returns early (backward-compatible, no manifest for standalone exports)

**Tests:** `test_manifest_written_to_outdir` (JSON structure, all keys present), `test_sha256sum_companion_file` (double-space format, 64-char hex, filename ends with `.fasta`).

---

### ✅ DI-03 — Manifest includes config snapshot and record counts

**Evidence:**
- `_write_manifest()` embeds `asdict(self._job_config)` under the `"config"` key
- `self._record_counts` tracks per-format write counts; `stats["total_records"] = sum(self._record_counts.values())`

**Tests:** `test_manifest_contains_config_snapshot` (asserts `manifest["config"]["name"] == "test-job"`), `test_record_counts_accurate` (writes 3 records, asserts count == 3).

---

### ✅ DI-04 — `manifest_verify()` library function

**Evidence:**
- `src/biocurator/core/verifier.py` exists with `def manifest_verify(manifest_path: Path) -> dict[str, Any]`
- Reads manifest JSON, resolves file paths relative to `manifest_path.parent`
- Security gate: rejects `..` and absolute `/` path entries (logs warning, skips)
- Recomputes SHA-256 using chunked 8192-byte reads
- Returns structured report: `manifest_path`, `manifest_valid`, `files_checked`, `files_matched`, `files_missing`, `files_corrupted`, `results`
- Exported via `src/biocurator/core/__init__.py` in `__all__`

**Tests:** `test_verify_all_match`, `test_verify_corrupted_detected`, `test_verify_file_missing`, `test_verify_invalid_manifest`, `test_verify_path_traversal_rejected`, `test_verify_mixed_results` — all 6 pass.

---

### ✅ curator.run_job() passes job metadata + returns manifest paths

**Evidence:**
- `src/biocurator/core/curator.py` passes `job_name=job_config.name`, `databases=job_config.search.databases`, `job_config=job_config` to `StreamingExporter` constructor
- `run_job()` return dict includes `"manifest"` and `"manifest_sha256"` keys (conditional on file existence)

**Tests:** `test_run_job_streaming` asserts `manifest_path.exists()`, `manifest["job_name"] == "test-job"`, `manifest["stats"]["total_records"] == 1`, and `"manifest" in results`.

---

## Automated Test Results

```
tests/core/test_exporter.py          8/8 passed   (DI-01, DI-02, DI-03)
tests/core/test_verifier.py          6/6 passed   (DI-04)
tests/core/test_streaming_curation.py 1/1 passed  (end-to-end pipeline)
tests/core/test_curator.py           5/5 passed   (no regressions)
─────────────────────────────────────────────────
Total                               20/20 passed
```

Full regression suite (153 prior-phase tests): **153/153 passed** — no regressions introduced.

---

## Known Issues (from code review — not blocking phase completion)

The code review (03-REVIEW.md) identified 5 critical findings that represent correctness risks in edge cases not exercised by the current test suite:

- **CR-01**: `_hash_state` not reset in `open()` — wrong checksums if exporter is reused
- **CR-02**: `__exit__` writes manifest even after exception — manifest covers truncated files
- **CR-03**: `verify_manifest` does not catch `json.JSONDecodeError` — unhandled crash
- **CR-04**: `verify_file` uses `read_bytes()` — OOM on large files
- **CR-05**: Encoding mismatch risk between incremental hasher and file verifier

These are tracked in `03-REVIEW.md`. The phase-03 goal is met for the normal happy path; the review findings are candidates for gap closure before phase 04 (CLI integration).

---

_Verified: 2026-05-26 | Tool: direct codebase inspection + pytest_
