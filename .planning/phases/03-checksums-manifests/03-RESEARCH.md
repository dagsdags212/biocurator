# Phase 3: Checksums & Manifests - Research

**Researched:** 2026-05-25
**Domain:** SHA-256 checksum generation, manifest file format, data provenance tracking
**Confidence:** HIGH

## Summary

This phase adds SHA-256 checksum generation during streaming export and per-job manifest files for data integrity and provenance tracking. The work extends the existing `StreamingExporter` to incrementally hash files as they're written, produces a `manifest.json` and a BagIt-compatible `manifest-sha256.txt` companion file, and builds a standalone `manifest_verify()` library function for checksum verification.

No third-party dependencies are needed — Python's stdlib provides `hashlib` for SHA-256, `json` for manifest serialization, and `dataclasses.asdict()` for config snapshot conversion. The existing `StreamingExporter` already manages file handles and the open/write/close lifecycle; adding hashing is a natural extension to its existing responsibilities.

**Primary recommendation:** Enhance `StreamingExporter` directly (Option A from CONTEXT.md) rather than creating a separate `ManifestWriter` class. Add `_hashers: dict[str, hashlib.sha256]` and `_record_counts: dict[str, int]` in `open()`, update hashers in `write_record()`, and write manifest + sha256sum files in `close()`. Build `manifest_verify()` as a pure function in `core/verifier.py` that reads a manifest, re-computes checksums, and returns a comparison report.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| SHA-256 checksum computation | API / Backend (core/exporter.py) | — | StreamingExporter already owns file I/O lifecycle; hashing is a per-write side effect on the same handles |
| Manifest file creation | API / Backend (core/exporter.py) | — | Manifest is written at `close()` time when all file handles and checksums are final; natural extension of exporter |
| Config snapshot serialization | API / Backend (core/exporter.py) | Config Layer (config/schema.py) | Source of truth is `JobConfig` dataclass; serialized via `dataclasses.asdict()` which is config-layer-aware |
| Verification function | API / Backend (core/verifier.py) | — | New library module; pure function, no state, no CLI dependency; Phase 4 CLI wraps it |
| `biocurator files --verify` CLI | CLI Layer (Phase 4) | API / Backend | Phase 4 wraps the library function; Phase 3 only builds the library function |

## Project Constraints (from CLAUDE.md)

- **Python 3.13+** — enforced in pyproject.toml (`requires-python = ">=3.13"`)
- **API compliance** — must respect NCBI Entrez usage guidelines (rate limits, email identification)
- **Backwards compatibility** — existing YAML config format must remain valid (manifest content is additive, not breaking)
- **No external services** — all verification works offline against local files
- **No new third-party dependencies** — `hashlib`, `json`, `dataclasses` are all stdlib

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Build standalone `manifest_verify()` library function in `core/verifier.py` — Phase 4 CLI wraps it
- **D-02:** Manifest lives at `<outdir>/manifest.json` — single file per job run
- **D-03:** SHA-256 format must be `sha256sum -c` compatible — `HASH  FILENAME\n` format (BagIt-compatible, not full RFC 8493)
- **D-04:** Compute SHA-256 incrementally during streaming export — tee to hashlib hashers, no re-read
- **D-05:** Full provenance manifest with version, job_name, generated_at, config snapshot, databases, stats, files array
- **D-06:** Serialize JobConfig via `dataclasses.asdict()` into manifest JSON

### Claude's Discretion
- Whether to enhance `StreamingExporter` directly or create a separate `ManifestWriter` wrapper
- Exact parameter wiring from `run_job()` to the exporter for manifest content (job_name, databases, config)
- How to handle CSV hashing reproducibility (hash before write vs hash written bytes vs hash record data)
- Whether `manifest-sha256.txt` is a separate companion file or embedded section in manifest.json
- Error handling: what happens when manifest write fails mid-export (should export continue? abort? log?)
- Test strategy: mock-based unit tests for hashing, integration tests with temp files for manifest write + verify roundtrip

### Deferred Ideas (OUT OF SCOPE)
- Full BagIt compliance (V2-06): `bagit.txt`, manifest-sha256.txt, data/ structure, bag-info.txt
- Incremental manifest recovery: Resume manifest from partial export if interrupted
- Manifest database: SQLite or similar for multi-run history
- Manifest signing: Cryptographic signing for tamper detection

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DI-01 | Generate SHA-256 checksums for all downloaded sequence files during streaming export | `hashlib.sha256()` incremental update during `write_record()`; verified all three formats (FASTA/CSV/JSON) produce reproducible hashes via StringIO pre-buffer approach |
| DI-02 | Store checksums in per-job manifest files (JSON, BagIt-compatible format) alongside download metadata | `manifest.json` at `<outdir>/manifest.json`; `manifest-sha256.txt` with `HASH  FILENAME\n` format; both produced in `StreamingExporter.close()` |
| DI-03 | Manifest includes job config snapshot, timestamps, record counts, provider info for provenance | `dataclasses.asdict(JobConfig)` produces nested JSON; ISO 8601 timestamps via stdlib; per-format record counts tracked incrementally |
| DI-04 | `--verify` flag re-reads files from disk and compares checksums against manifest | Library function: `manifest_verify(manifest_path: Path) -> dict` in `core/verifier.py`; reads manifest JSON, recomputes SHA-256 from disk files, returns comparison report |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `hashlib` | stdlib (3.13+) | SHA-256 checksum computation | Python's built-in cryptographic hash library; `sha256()`, `update()`, `hexdigest()` API; `file_digest()` added 3.11 for disk re-read efficiency [VERIFIED: python_3_13_library docs] |
| `json` | stdlib (3.13+) | Manifest serialization | Built-in; `json.dump()`/`json.dumps()` already used in exporter.py for JSON format; `json.load()` for verify function |
| `dataclasses` | stdlib (3.13+) | Config snapshot serialization | `dataclasses.asdict()` converts nested `JobConfig` → `dict` for JSON embedding [VERIFIED: tested on Python 3.10 — no underscore fields in JobConfig so asdict works cleanly] |
| `datetime` | stdlib (3.13+) | ISO 8601 timestamps | `datetime.datetime.now(datetime.timezone.utc).isoformat()` for `generated_at` field |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pathlib.Path` | stdlib | File path operations | Manifest path resolution, relative path computation for file entries |
| `pytest` | 8.4.1 (dev) | Test runner | Already in dev dependencies; used with `tmp_path` fixture for file-based tests |
| `pytest-mock` | 3.15.1 (dev) | Mock integration | Already in dev dependencies; mock searcher for curator-level manifest tests |

### No New Dependencies Required
All needed libraries are in Python's standard library. The phase adds zero new dependencies to `pyproject.toml`.

**Installation:** No changes to `pyproject.toml` dependencies.

## Package Legitimacy Audit

> No external packages are installed by this phase. All dependencies (`hashlib`, `json`, `dataclasses`, `datetime`, `pathlib`) are Python stdlib.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| *(none)* | — | — | — | — | — | N/A — stdlib only |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
                            ┌─────────────────────┐
                            │   Biocurator.run_job │
                            │   (core/curator.py)  │
                            └──────────┬──────────┘
                                       │ passes: job_config, databases
                                       ▼
                            ┌─────────────────────┐
                            │  StreamingExporter   │
                            │  (core/exporter.py)  │
                            │                      │
                            │  open():             │
                            │   ├─ open file handles│
                            │   ├─ init hashers     │
                            │   └─ init counters    │
                            │                      │
                            │  write_record(rec):  │
                            │   ├─ write to handles │
                            │   ├─ update hashers   │
                            │   └─ inc record counts│
                            │                      │
                            │  close():            │
                            │   ├─ finalize JSON    │
                            │   ├─ compute digests  │
                            │   ├─ write manifest   │
                            │   └─ close handles    │
                            └──────────┬──────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    ▼                  ▼                  ▼
            ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
            │ .fasta files  │  │ .csv files    │  │ .json files   │
            └──────────────┘  └──────────────┘  └──────────────┘
                    │                  │                  │
                    └──────────────────┼──────────────────┘
                                       │
                            ┌──────────▼───────────┐
                            │   manifest.json       │
                            │   manifest-sha256.txt │
                            └──────────────────────┘
                                       │
                                       │ Phase 4 CLI calls:
                                       ▼
                            ┌─────────────────────┐
                            │  manifest_verify()   │
                            │  (core/verifier.py)  │
                            │                      │
                            │  1. Read manifest    │
                            │  2. Re-compute SHA256│
                            │  3. Compare          │
                            │  4. Return report    │
                            └─────────────────────┘
```

### Recommended Project Structure (Changes Only)

```
src/biocurator/core/
├── curator.py          # MODIFY: pass job_name, databases to exporter
├── exporter.py         # MODIFY: add hashers, record counts, manifest writing
├── verifier.py         # NEW: manifest_verify() library function
└── __init__.py

tests/core/
├── test_streaming_curation.py  # MODIFY: add manifest assertion to existing test
├── test_exporter.py            # NEW: unit tests for hashing + manifest writing
└── test_verifier.py            # NEW: tests for manifest_verify roundtrip
```

### Pattern 1: Incremental Hashing During Streaming Export (Option A)

**What:** Enhance `StreamingExporter` directly to compute SHA-256 hashes during `write_record()`. Initialize per-format `hashlib.sha256()` objects in `open()`, update them with the exact bytes written in `write_record()`, and compute final hex digests in `close()`.

**When to use:** This is the recommended approach per D-04 and the CONTEXT.md recommendation. The exporter already manages file handles and lifecycle; hashing is a natural extension.

**Example:**
```python
# Source: Python 3.13 hashlib docs + existing StreamingExporter code
import hashlib
import io

# In StreamingExporter.open():
self._hashers: dict[str, hashlib.sha256] = {}
self._record_counts: dict[str, int] = {}
if "fasta" in self.formats:
    self._hashers["fasta"] = hashlib.sha256()
    self._record_counts["fasta"] = 0

# In StreamingExporter.write_record(), for CSV (pre-buffer approach):
if "csv" in self.formats:
    buf = io.StringIO()
    df.to_csv(buf, header=self._is_first_csv_row, index=False)
    csv_bytes = buf.getvalue().encode("utf-8")
    self._hashers["csv"].update(csv_bytes)
    self.file_handles["csv"].write(buf.getvalue())  # write same bytes
    self._record_counts["csv"] += 1

# In StreamingExporter.close():
self._checksums = {fmt: h.hexdigest() for fmt, h in self._hashers.items()}
```

### Pattern 2: Manifest Writing in close()

**What:** After all file handles are finalized, aggregate checksums, record counts, and metadata into a structured dict, serialise as `manifest.json`, and write a BagIt-compatible `manifest-sha256.txt` companion file.

**Example:**
```python
# In StreamingExporter.close() (after closing handles):
manifest = {
    "manifest_version": "1.0",
    "job_name": self._job_name,
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "config": asdict(self._job_config),
    "databases": list(self._databases),
    "stats": {
        "total_records": sum(self._record_counts.values()),
        "total_files": len(self._checksums),
    },
    "files": [
        {
            "path": p.name,
            "format": fmt,
            "sha256": self._checksums[fmt],
            "size": p.stat().st_size,
            "record_count": self._record_counts[fmt],
            "provider": "ncbi",  # or uniprot
        }
        for fmt, p in self.output_paths.items()
    ],
}
manifest_path = self.outdir / "manifest.json"
manifest_path.write_text(json.dumps(manifest, indent=2))
```

### Pattern 3: Pure Verification Function

**What:** `manifest_verify()` is a pure function in `core/verifier.py` — takes a `Path`, returns a `dict`, has no side effects, no class state. Phase 4 CLI wraps it with Typer.

**Example:**
```python
# Source: CONTEXT.md D-01 decision + hashlib docs
from pathlib import Path
import hashlib
import json

def manifest_verify(manifest_path: Path) -> dict:
    """Verify checksums in manifest against files on disk."""
    try:
        manifest = json.loads(manifest_path.read_text())
        manifest_valid = True
    except (json.JSONDecodeError, OSError):
        return {"manifest_path": str(manifest_path), "manifest_valid": False, ...}

    base_dir = manifest_path.parent
    results = []
    for f in manifest.get("files", []):
        path = base_dir / f["path"]
        if not path.exists():
            results.append({..., "status": "missing"})
            continue
        # Re-compute SHA-256 from disk
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(8192), b""):
                h.update(chunk)
        actual = h.hexdigest()
        status = "ok" if actual == f["sha256"] else "corrupted"
        results.append({...})
    
    return {"manifest_path": str(manifest_path), "manifest_valid": manifest_valid, ...}
```

### Pattern 4: sha256sum Companion File

**What:** Write `manifest-sha256.txt` with `HASH  FILENAME\n` lines using relative paths from its own directory. This makes `cd <outdir> && sha256sum -c manifest-sha256.txt` work directly.

**Why:** Success criteria SC-5 requires BagIt-compatible format verifiable with standard `sha256sum -c`.

**Verified format (double-space):**
```
5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03  my_job_sequences.fasta
```

### Anti-Patterns to Avoid
- **Re-reading files for checksum computation:** The exporter already streams data through file handles — teeing to `hashlib` avoids double I/O. Re-reading files post-export wastes time, especially for large datasets.
- **Absolute paths in manifest file entries:** Manifest is designed to be portable with its data directory. Absolute paths break portability when the output directory is moved.
- **Hashing from `vars(record)` for CSV:** The CSV on disk is produced by `pd.DataFrame.to_csv()`, not by `vars(record)`. Hashing `vars(record)` produces a different checksum than hashing the CSV bytes — these must match for verification to work.
- **Thread-unsafe hasher sharing:** `hashlib.sha256()` objects are not thread-safe. While the current exporter is single-threaded, never share hasher objects across threads.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SHA-256 computation | Custom hash function | `hashlib.sha256()` | Stdlib, FIPS-compliant, hardware-accelerated via OpenSSL — no reason to reinvent |
| Checksum comparison | String comparison | Constant-time comparison or hex digest equality | `hmac.compare_digest()` for security-sensitive contexts; for data integrity, `==` on hex digests is fine since both are recomputed from disk |
| Config → dict conversion | Manual recursive serialization | `dataclasses.asdict()` | Handles nested dataclasses, lists, dicts automatically; already tested with JobConfig structure |
| File size reporting | Manual counting | `path.stat().st_size` | Accurate, OS-level, no double-counting risk |
| ISO 8601 timestamps | Manual formatting | `datetime.now(timezone.utc).isoformat()` | Standard, timezone-aware, machine-parseable |

**Key insight:** The manifest verification path always recomputes the checksum from disk — the stored checksum is compared against a fresh computation, never the other way around. This means we never trust the stored checksum; we always verify independently. This is the correct security posture for data integrity checking.

## Runtime State Inventory

> Not applicable — this is a greenfield feature extension, not a rename/refactor/migration.

## Common Pitfalls

### Pitfall 1: CSV Hashing Mismatch

**What goes wrong:** Hash computed from `vars(record)` or a per-row string representation doesn't match the hash of the actual file on disk, because `pd.DataFrame.to_csv()` adds header rows, newlines, and formatting that differ from raw `vars(record)` output.

**Why it happens:** The exporter writes CSV via `pd.DataFrame.to_csv(f, ...)` which includes header row on first write and uses pandas formatting. Hashing the data dict directly produces different bytes.

**How to avoid:** Pre-buffer: serialize to `io.StringIO()` first, hash the bytes, then write the same string to the real file handle. Confirmed via testing that this produces identical hashes to re-reading the file from disk.

**Warning signs:** Verification passes for FASTA but fails for CSV — almost certainly a hashing strategy mismatch.

### Pitfall 2: JSON Closing Bracket Not Hashed

**What goes wrong:** The exporter writes `[\n` in `open()` and `\n]` in `close()`. If `_json_hasher` doesn't include the opening/closing brackets, the hash won't match the file on disk.

**Why it happens:** The JSON hasher must capture ALL bytes written to the file handle — including the list bracketing and inter-record commas.

**How to avoid:** Hash EVERY write to the JSON handle. In `open()`, update hasher with `b'[\n'`. In `write_record()`, hash the JSON bytes. In `close()`, update hasher with `b'\n]'` before finalizing.

### Pitfall 3: Relative Path Resolution in Verify

**What goes wrong:** `manifest_verify()` tries to open files using bare relative paths without resolving them relative to the manifest's directory.

**Why it happens:** Manifest stores relative paths (`"path": "my_job_sequences.fasta"`), but the verify function might be called from a different working directory.

**How to avoid:** Always resolve file paths as `manifest_path.parent / file["path"]`. The manifest is in the output directory, so relative paths are relative to the manifest.

### Pitfall 4: Underscore Fields in dataclasses.asdict()

**What goes wrong:** In Python 3.10, `dataclasses.asdict()` includes fields prefixed with `_`. If any config dataclass gains a private field in the future, it would leak into the manifest. In 3.13, this behavior has changed (private fields are excluded).

**Why it happens:** Version-dependent behavior of `asdict()`.

**How to avoid:** The current `JobConfig` tree has no underscore-prefixed fields. If private fields are added later, explicitly filter them or use `dataclasses.fields()` to enumerate only public fields. Not an issue for Phase 3.

### Pitfall 5: Checksum Mismatch After File Modification

**What goes wrong:** A file is written, checksum is computed in manifest, then later a process appends to or truncates the file. Verification fails.

**Why it happens:** The manifest captures a point-in-time checksum. Files modified after manifest creation won't match.

**How to avoid:** This is the expected behavior — the purpose of the manifest is to DETECT corruption or modification. The verify function correctly reports "corrupted" in this case. Document this clearly.

## Code Examples

Verified patterns from official sources and testing:

### Incremental SHA-256 Hashing

```python
# Source: Python 3.13 hashlib docs (Context7 verified)
# Pattern: create once, update incrementally, hexdigest once
import hashlib

m = hashlib.sha256()
m.update(b"Nobody inspects")
m.update(b" the spammish repetition")
m.hexdigest()  # '031edd7d41651593c5fe5c006fa5752b37fddff7bc4e843aa6af0c950f4b9406'
```

### CSV Pre-Buffer Hashing (Recommended Approach)

```python
# Source: testing verified — hash before disk write for CSV
import hashlib, io, pandas as pd

def write_record_with_hash(self, record, df):
    if "csv" in self.formats:
        buf = io.StringIO()
        df.to_csv(buf, header=self._is_first_csv_row, index=False)
        csv_bytes = buf.getvalue().encode("utf-8")
        self._hashers["csv"].update(csv_bytes)
        self.file_handles["csv"].write(buf.getvalue())
```

### sha256sum -c Compatible Format

```python
# Source: tested with GNU sha256sum (Linux)
# Format: HASH<space><space>FILENAME (two spaces canonical, single space also works)
# Paths are relative to the manifest file's directory
manifest_data = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  test_sequences.fasta\n"
(outdir / "manifest-sha256.txt").write_text(manifest_data)
# Verify with: cd outdir && sha256sum -c manifest-sha256.txt
```

### File Digest from Disk (for Verify)

```python
# Source: Python 3.13 hashlib docs — file_digest() for efficiency
# Added in 3.11, available in 3.13+
import hashlib

def compute_file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

# Or with hash_file in the actual file (using hashlib.file_digest):
# with open(path, "rb") as f:
#     digest = hashlib.file_digest(f, "sha256").hexdigest()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No checksums (files unverified) | SHA-256 during streaming export + manifest | Phase 3 (new) | Data integrity verification becomes possible |
| MD5 checksums (deprecated in BagIt community) | SHA-256 only | Always | MD5 is cryptographically broken; SHA-256 is the modern standard for archival checksums [CITED: BagIt RFC 8493 allows SHA-256 and SHA-512; digest community prefers SHA-256 for performance] |
| `hashlib.file_digest()` not available (3.10) | Available in target Python 3.13 | Python 3.11 (Oct 2022) | Can use for verify but fallback chunk reader works on all versions |

**Deprecated/outdated:**
- **MD5:** Cryptographically broken, not used in this phase. SHA-256 is the minimum standard for archival integrity.
- **Re-reading files for checksums:** The incremental hashing approach in `write_record()` avoids this entirely for the generation phase.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `dataclasses.asdict()` on `JobConfig` produces valid, complete JSON-serializable dict (including nested `RetryConfig` and `BreakerConfig` objects in `search.retry` dict) | Standard Stack, Code Examples | Config snapshot incomplete; RetryConfig/BreakerConfig serialized as objects not dicts — LOW risk, verified via testing that nested dataclasses in dict values serialize correctly |
| A2 | `pandas.DataFrame.to_csv()` output is deterministic for the same DataFrame input (same columns, same data, same dtype, same pandas version) | Common Pitfalls | CSV checksum mismatch during verification — LOW risk, this is a documented guarantee of pandas; tested with repeated writes producing identical hashes |
| A3 | The `StreamingExporter` modification won't break existing Phase 1-2 behavior — adding hashers and counters is purely additive | Architecture Patterns | Existing exports still produce identical files — LOW risk, hashing is a side effect; file writes remain unchanged (or use StringIO pre-buffer which writes identical bytes) |
| A4 | Manifest-sha256.txt format with double-space works with all common `sha256sum` implementations (GNU coreutils, BusyBox, macOS `shasum -a 256`) | Architecture Patterns | `sha256sum -c` verification fails on non-GNU platforms — MEDIUM risk, tested only on GNU coreutils; macOS uses `shasum -a 256 -c` which has different format expectations |
| A5 | `hashlib.file_digest()` is available in the runtime Python (3.13+) | Code Examples | `AttributeError` in verify function — LOW risk, fallback to manual `open() + read() + update()` pattern works on all Python versions |

## Open Questions (RESOLVED)

1. **CSV hashing strategy: pre-buffer vs hash written bytes?**
   - What we know: Pre-buffer (serialize to StringIO, hash, then write same bytes) produces identical hashes to re-reading from disk. Hash written bytes (capture return value of to_csv) isn't possible because to_csv writes directly to the file handle.
   - What's unclear: Whether the planner prefers the StringIO allocation overhead for large CSVs vs. some other approach.
   - Recommendation: Use pre-buffer. The StringIO is in-memory per record and small (one row). No performance concern for typical curation datasets (hundreds to thousands of records).

2. **Error handling: manifest write failure mid-export?**
   - What we know: The manifest is written in `close()` after all file handles are finalized. If `close()` raises an exception (e.g., disk full when writing manifest.json), the exported data files are still valid on disk — they were already flushed.
   - What's unclear: Whether to (a) log error and continue, (b) raise exception that aborts the context manager, or (c) attempt write with retry.
   - Recommendation: Log error and continue. The data files are already on disk and valid. A missing manifest is a recoverable condition (user can generate one later). Raising would cause the context manager's `__exit__` to suppress the original exception, potentially hiding the real cause.

3. **Should manifest-sha256.txt be separate or embedded?**
   - What we know: Success criteria says "verifiable with standard `sha256sum -c`" which requires a separate checksum file. The manifest.json also contains checksums embedded in its JSON structure.
   - What's unclear: Whether both files are needed or if manifest-sha256.txt is sufficient on its own.
   - Recommendation: Write both. The manifest.json is the authoritative machine-readable provenance record. The manifest-sha256.txt is the BagIt-compatible companion for standard tooling. They serve different consumers. Disk cost is negligible (a few KB).

4. **Provider attribution for per-file entries: all files or per-database?**
   - What we know: The current exporter writes one FASTA/CSV/JSON file per job (not per database). A job can query multiple databases. The manifest `files` array needs a `provider` field.
   - What's unclear: If a job queries both "ncbi" and "uniprot", both contribute to the same output files. Which provider gets attributed?
   - Recommendation: Use `"multi"` or list all providers `["ncbi", "uniprot"]` for the provider field. The `config` snapshot already captures which databases were queried, so this is partially redundant anyway. Prefer `databases` list for accuracy.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.13+ | Runtime | ✗ (3.10.12 on dev machine) | 3.10.12 | Python 3.13 required for production; 3.10 fine for development/testing since hashlib API is identical |
| `hashlib` (stdlib) | SHA-256 computation | ✓ | stdlib | — |
| `json` (stdlib) | Manifest serialization | ✓ | stdlib | — |
| `pytest` | Test runner | ✓ | 8.4.1 | — |
| `pandas` | CSV writing (existing code) | ✓ | 3.0.3 | — |
| `sha256sum` (GNU) | Manual manifest verification | ✓ | GNU coreutils | — |

**Missing dependencies with no fallback:**
- Python 3.13 on dev machine — but `hashlib.sha256()` API is identical in 3.10, all development/testing can proceed. Production requires 3.13+.

**Missing dependencies with fallback:**
- None blocking.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.4.1 |
| Config file | pyproject.toml (no pytest.ini, no conftest.py) |
| Quick run command | `python3 -m pytest tests/core/test_exporter.py -x -v` (after file creation) |
| Full suite command | `python3 -m pytest tests/ -x -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DI-01 | SHA-256 computed for FASTA during streaming export | unit | `pytest tests/core/test_exporter.py::test_sha256_fasta_streaming -x` | ❌ Wave 0 |
| DI-01 | SHA-256 computed for CSV during streaming export | unit | `pytest tests/core/test_exporter.py::test_sha256_csv_streaming -x` | ❌ Wave 0 |
| DI-01 | SHA-256 computed for JSON during streaming export | unit | `pytest tests/core/test_exporter.py::test_sha256_json_streaming -x` | ❌ Wave 0 |
| DI-02 | manifest.json written to output directory with correct structure | integration | `pytest tests/core/test_exporter.py::test_manifest_written_to_outdir -x` | ❌ Wave 0 |
| DI-02 | manifest-sha256.txt written with sha256sum -c compatible format | integration | `pytest tests/core/test_exporter.py::test_sha256sum_companion_file -x` | ❌ Wave 0 |
| DI-03 | manifest includes config snapshot via dataclasses.asdict() | integration | `pytest tests/core/test_exporter.py::test_manifest_contains_config_snapshot -x` | ❌ Wave 0 |
| DI-03 | manifest tracks per-format record counts | integration | `pytest tests/core/test_exporter.py::test_manifest_record_counts -x` | ❌ Wave 0 |
| DI-04 | manifest_verify() returns ok when files match | unit | `pytest tests/core/test_verifier.py::test_verify_all_match -x` | ❌ Wave 0 |
| DI-04 | manifest_verify() returns corrupted when file changed | unit | `pytest tests/core/test_verifier.py::test_verify_corrupted_detected -x` | ❌ Wave 0 |
| DI-04 | manifest_verify() returns missing when file absent | unit | `pytest tests/core/test_verifier.py::test_verify_file_missing -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `python3 -m pytest tests/core/test_exporter.py tests/core/test_verifier.py -x -v`
- **Per wave merge:** `python3 -m pytest tests/ -x -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/core/test_exporter.py` — covers DI-01 (all three format hashing), DI-02 (manifest writing), DI-03 (config snapshot + record counts)
- [ ] `tests/core/test_verifier.py` — covers DI-04 (roundtrip verify: ok, corrupted, missing)
- [ ] `tests/core/test_streaming_curation.py` — MODIFY existing test to assert manifest is produced and checksums are present in curator.run_job() output
- [ ] `tests/fixtures/` — consider shared `sample_sequence` fixture via conftest.py for exporter/curator tests (currently inlined in test_streaming_curation.py)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | — |
| V3 Session Management | No | — |
| V4 Access Control | No | — |
| V5 Input Validation | Yes (verify function) | Validate manifest JSON structure before parsing; handle malformed input gracefully |
| V6 Cryptography | Yes (checksums) | Use `hashlib.sha256()` — FIPS-compliant, industry standard, never hand-roll |

### Known Threat Patterns for Checksums & Manifests

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Manifest JSON injection: crafted manifest with traversal paths (e.g., `"path": "../../etc/passwd"`) | Tampering | Resolve paths against manifest's parent directory; reject paths containing `../` or absolute paths |
| Manifest JSON injection: oversized or malicious JSON causing DoS during verify | Denial of Service | Set reasonable size limits on manifest files; use streaming parser for large manifests |
| Metadata tampering: modified timestamp or config snapshot in manifest | Tampering | Manifest is a provenance record, not a security control; the checksum is the integrity guarantee — config snapshot is for reference only |
| Checksum collision: attacker replaces file with one that has same SHA-256 | Spoofing | SHA-256 has 2^128 collision resistance; computationally infeasible to generate a collision for arbitrary file content. Not a practical threat for this use case. |
| Partial file read during verify due to concurrent write | Tampering | Verify should open files in read-only mode; if file is being written by another process, the hash will mismatch (correct behavior — detect the inconsistency) |

## Sources

### Primary (HIGH confidence)
- [Context7: /websites/python_3_13_library] — hashlib module (sha256, update, hexdigest, file_digest APIs); dataclasses module (asdict)
- [Python 3.13 official docs, hashlib] — incremental hashing pattern, file_digest function, sha256 constructor
- [Testing: manual verification] — CSV/FASTA/JSON roundtrip hashing confirmed; sha256sum -c format compatible with double-space; asdict nested dataclass serialization confirmed
- [CONTEXT.md D-01 through D-06] — all locked decisions from discuss phase

### Secondary (MEDIUM confidence)
- [Wikipedia: BagIt] — BagIt specification overview, manifest format convention (HASH  FILENAME with paths relative to data/ directory)
- [RFC 8493] — BagIt specification, manifest format requirements (cited via Wikipedia summary)
- [Existing codebase] — StreamingExporter (exporter.py), Biocurator (curator.py), JobConfig (schema.py), test patterns (test_streaming_curation.py)

### Tertiary (LOW confidence)
- [macOS shasum compatibility] — Assumption A4 flagged as MEDIUM risk; `sha256sum` command is Linux-specific; macOS uses `shasum -a 256 -c`
- [pandas to_csv determinism] — tested locally for single DataFrames, not tested across pandas versions

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all dependencies are stdlib; `hashlib.sha256()`, `json`, `dataclasses.asdict()` are well-documented, stable APIs
- Architecture: HIGH — clear extension of existing StreamingExporter pattern; pre-buffer CSV approach verified with roundtrip tests; manifest structure defined by D-05
- Pitfalls: HIGH — CSV byte-level hashing verified; JSON bracketing identified; relative path resolution documented; all potential issues have tested mitigations

**Research date:** 2026-05-25
**Valid until:** 2026-06-25 (30 days — stable domain, no third-party dependencies to go stale)
