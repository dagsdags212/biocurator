# Phase 3: Checksums & Manifests — Context

**Gathered:** 2026-05-25
**Status:** Ready for planning

## Phase Boundary

SHA-256 checksum generation during streaming export, per-job manifest JSON files with provenance metadata, and a standalone verify library function that re-reads files from disk and compares checksums. The CLI `--verify` flag (`biocurator files --verify`) is Phase 4 — this phase builds only the library-level verify function that Phase 4 will call.

**In scope:**
- SHA-256 checksum computation during streaming export (DI-01)
- Per-job manifest JSON with checksums, record counts, timestamps (DI-02)
- Config snapshot embedded in manifest for provenance (DI-03)
- Standalone `manifest_verify()` function to re-read and compare (DI-04 library part)

**Out of scope:**
- `biocurator files --verify` CLI command (Phase 4, CLI-03)
- Full RFC 8493 BagIt structural compliance (v2)
- `biocurator files` / `biocurator jobs` commands (Phase 4)
- Manifest database storage (v2)
- Checkpoint persistence for in-progress manifests (v2)

## Implementation Decisions

### DI-04 Scope Boundary
- **D-01:** Build a standalone `manifest_verify()` library function in Phase 3 (e.g., in `core/verifier.py`). Phase 4 CLI (`biocurator files --verify`) wraps it. The verify function reads a manifest file, re-computes SHA-256 for each listed file, and returns a comparison report.
- **Rationale:** Clean library/CLI separation follows existing patterns (RetryConfig → CLI, HealthChecker → status). Phase 4 integration is a thin CLI wrapper over this function.

### Manifest Location
- **D-02:** Manifest lives at `<outdir>/manifest.json` — single file per job run in the export output directory.
- **Rationale:** Simple, self-contained. If the output dir is `my_job_out/`, the manifest is `my_job_out/manifest.json`. This keeps manifest and data together for portability.

### BagIt Compatibility
- **D-03:** SHA-256 format must be `sha256sum -c` compatible — i.e., the manifest (or a companion file) uses `HASH  FILENAME\n` format. Full RFC 8493 BagIt structural compliance (bagit.txt, data/ subdirectory, bag-info.txt) is deferred to v2.
- **Rationale:** Success criteria says "verifiable with standard `sha256sum -c`". The double-space hash format is sufficient to meet this. Full BagIt adds structural requirements that don't improve the v1 use cases.

### Hashing Strategy
- **D-04:** Compute SHA-256 incrementally during streaming export. Each `write_record()` call updates the appropriate format hasher with the bytes written. Final digest and close happens in `close()`.
- **Rationale:** Avoids re-reading files from disk. Since the exporter already streams data to open file handles, we can tee to hashlib hashers at the same time. Efficient for large datasets with no double I/O.

### Manifest Content
- **D-05:** Full provenance manifest with:
  - `manifest_version` (string, "1.0")
  - `job_name` (string)
  - `generated_at` (ISO 8601 timestamp)
  - `config` (JobConfig serialized as JSON)
  - `databases` (list of provider names queried)
  - `stats` (total_records, total_files)
  - `files` (array of per-file objects: `path`, `format`, `sha256`, `size`, `record_count`, `provider`)
- **Rationale:** Comprehensive provenance tracking. Every file links back to its provider, format, and checksum. The config snapshot enables re-running the same job later.

### Config Snapshot Format
- **D-06:** Serialize the relevant `JobConfig` dataclass instance as a JSON object in the manifest. Use `dataclasses.asdict()` or equivalent for conversion.
- **Rationale:** JSON is more portable than embedded YAML. The manifest doesn't need the original YAML file to be present for verification. Clean machine-readable format for querying provenance.

## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing Code Patterns
- `src/biocurator/core/exporter.py` — `StreamingExporter` class (modify for incremental hashing + manifest writing)
- `src/biocurator/core/curator.py` — `Biocurator.run_job()` (current export + manifest wiring, ~line 127–286)
- `src/biocurator/providers/base.py` — `SequenceRecord` dataclass (fields serialized via `vars()`)
- `src/biocurator/config/schema.py` — `JobConfig`, `ExportConfig`, `SearchConfig`, `FilterConfig` dataclasses (config snapshot target)
- `src/biocurator/config/loader.py` — ConfigLoader pattern for file I/O
- `tests/core/test_streaming_curation.py` — existing streaming export tests (reference for test patterns)
- `tests/core/test_curator.py` — existing curator tests (export assertions)

### Dependencies
- `hashlib` — stdlib, already available (Python 3.13+)
- `json` — stdlib, already used in exporter.py
- `dataclasses.asdict()` — stdlib, for JobConfig → JSON serialization
- No new third-party dependencies needed

## Existing Code Insights

### Reusable Assets
- `StreamingExporter.open()` — already opens file handles per format; add hasher init here
- `StreamingExporter.write_record()` — already writes bytes to handles; add `hasher.update()` here
- `StreamingExporter.close()` — already finalizes files; add hasher digest + manifest write here
- `StreamingExporter.get_output_files()` — already returns `dict[str, Path]`; add manifest path in the same call
- `Biocurator.run_job()` line 151 — `StreamingExporter(...)` context manager already from `export_config` fields
- `vars(record)` — already used for CSV/JSON serialization; same fields feed manifest record counts

### Established Patterns
- **Config dataclass → JSON**: Phase 2 used dataclasses for configuration; Phase 3 extends this to manifest serialization
- **Streaming/iterator pattern**: `fetch_metadata()` and `download()` already yield `SequenceRecord`; manifest writing follows same incrementality
- **Context manager**: `StreamingExporter` already uses `__enter__/__exit__`; manifest file opening/closing fits this pattern
- **CLI/library separation**: `cli/commands/` → `core/` call pattern established in Phase 1-2; `core/verifier.py` → Phase 4 CLI follows this

### Integration Points
- `StreamingExporter.__init__()` — may need additional params (job_name, database list) for manifest content
- `Biocurator.run_job()` line 286 — currently returns `exporter.get_output_files()`; should also return manifest path
- `Biocurator.run_job()` lines 271–284 — this is where `exporter.write_record(seq_record)` is called; record count tracking lives here
- `StreamingExporter.close()` — post-export, this is where manifest JSON + sha256sum companion file get written

## Specific Ideas

### Manifest Structure (Extended)

```json
{
  "manifest_version": "1.0",
  "job_name": "my_job",
  "generated_at": "2026-05-25T14:30:00Z",
  "config": { /* JobConfig as_dict() */ },
  "databases": ["ncbi", "uniprot"],
  "stats": {
    "total_records": 42,
    "total_files": 2
  },
  "files": [
    {
      "path": "my_job_out/my_job_sequences.fasta",
      "format": "fasta",
      "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "size": 12345,
      "record_count": 20,
      "provider": "ncbi"
    }
  ]
}
```

Note: The `path` in files entries should be relative to the output directory (not absolute) for portability.

### sha256sum Companion File

In addition to `manifest.json`, write `manifest-sha256.txt` in `sha256sum -c` compatible format:
```
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  my_job_sequences.fasta
```
This file uses relative paths (relative to its own directory) so `cd outdir && sha256sum -c manifest-sha256.txt` works directly.

### verify() Function Signature

```python
def manifest_verify(manifest_path: Path) -> dict:
    """Verify checksums in manifest against files on disk.
    
    Returns: dict with keys:
        - manifest_path: str
        - manifest_valid: bool (manifest JSON parseable)
        - files_checked: int
        - files_matched: int
        - files_missing: int
        - files_corrupted: int
        - results: list of per-file {path, sha256_expected, sha256_actual, status}
    """
```

### Design Option: ManifestWriter vs Enhanced Exporter

The planner should consider two approaches:
- **Option A**: Enhance `StreamingExporter` to handle hashing + manifest writing directly (fewer classes, cohesive)
- **Option B**: Separate `ManifestWriter` class that wraps the exporter (separation of concerns, exporter stays simpler)

Recommendation: Option A — the exporter already manages file handles, open/close lifecycle, and knows about formats. Adding hashing and manifest writing is a natural extension. A separate class would duplicate file tracking.

### Hashing Implementation Detail

```python
import hashlib

# In open():
self._hashers: dict[str, hashlib.sha256] = {}
if "fasta" in self.formats:
    self._hashers["fasta"] = hashlib.sha256()
if "csv" in self.formats:
    self._hashers["csv"] = hashlib.sha256()
if "json" in self.formats:
    self._hashers["json"] = hashlib.sha256()

# In write_record(), after writing bytes to file handle:
if "fasta" in self.file_handles and record.sequence:
    data = f">{record.accession} {desc}\n{record.sequence}\n"
    self._hashers["fasta"].update(data.encode("utf-8"))

# In close(), before closing handles:
for fmt, hasher in self._hashers.items():
    checksum = hasher.hexdigest()
    self._checksums[fmt] = checksum
```

Note: CSV hashing must capture the exact bytes written via `pd.DataFrame.to_csv()` for the checksum to be reproducible. The simplest approach is to hash the `record` data before writing or hash the formatted CSV string.

### Record Count Tracking

The exporter currently doesn't track record counts per format. Add `self._record_counts: dict[str, int]` initialized in `open()` and incremented in `write_record()`.

## Deferred Ideas

- **Full BagIt compliance** (V2-06): `bagit.txt`, manifest-sha256.txt, data/ structure, bag-info.txt — deferred to v2
- **Incremental manifest recovery**: Resume manifest from partial export if interrupted — deferred to v2
- **Manifest database**: SQLite or similar for multi-run history — deferred to v2
- **Manifest signing**: Cryptographic signing for tamper detection — out of scope

## Agent's Discretion

- Whether to enhance `StreamingExporter` directly or create a separate `ManifestWriter` wrapper
- Exact parameter wiring from `run_job()` to the exporter for manifest content (job_name, databases, config)
- How to handle CSV hashing reproducibility (hash before write vs hash written bytes vs hash record data)
- Whether `manifest-sha256.txt` is a separate companion file or embedded section in manifest.json
- Error handling: what happens when manifest write fails mid-export (should export continue? abort? log?)
- Test strategy: mock-based unit tests for hashing, integration tests with temp files for manifest write + verify roundtrip

---

*Phase: 03-checksums-manifests*
*Context gathered: 2026-05-25*
