# Phase 03: Checksums & Manifests — Pattern Map

**Mapped:** 2026-05-25
**Files analyzed:** 6 (4 new, 2 modified)
**Analogs found:** 6 / 6

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/biocurator/core/exporter.py` (MODIFY) | core/service | file-I/O + streaming | self (extending own patterns) | self |
| `src/biocurator/core/curator.py` (MODIFY) | core/orchestrator | request-response + streaming | self (extending own patterns) | self |
| `src/biocurator/core/verifier.py` (NEW) | utility/library | file-I/O (read → compute → return) | `src/biocurator/config/loader.py` | role-match |
| `tests/core/test_exporter.py` (NEW) | test (unit/integration) | file-I/O (tmp files → assert) | `tests/core/test_streaming_curation.py` | exact |
| `tests/core/test_verifier.py` (NEW) | test (unit) | file-I/O (create → call → assert) | `tests/utils/test_logging.py` | exact |
| `tests/core/test_streaming_curation.py` (MODIFY) | test (integration) | streaming | self (extending own patterns) | self |

## Pattern Assignments

### `src/biocurator/core/exporter.py` (core/service, file-I/O + streaming) — MODIFY

**Analog:** Self — the file already establishes its own patterns; new code must extend them consistently.

**Imports pattern** (lines 1-18):
```python
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, TextIO
import pandas as pd
from biocurator.providers.base import SequenceRecord
from biocurator.utils.logging import get_logger

logger = get_logger(__name__)
```

**New imports to add** (following existing import conventions):
```python
import hashlib
from datetime import datetime, timezone
from dataclasses import asdict
from biocurator.config.schema import JobConfig
```

**Instance variable initialization pattern** (lines 42-50) — extend same block:
```python
self.outdir = outdir
self.prefix = prefix
self.formats = formats
self.outdir.mkdir(parents=True, exist_ok=True)

self.file_handles: Dict[str, TextIO] = {}
self.output_paths: Dict[str, Path] = {}
self.metadata_buffer: List[SequenceRecord] = []
self._is_first_csv_row = True
# NEW — add alongside existing init:
self._hashers: dict[str, hashlib.sha256] = {}
self._record_counts: dict[str, int] = {}
self._checksums: dict[str, str] = {}
self._job_name: str | None = None
self._databases: list[str] = []
self._job_config: JobConfig | None = None
```

**`open()` pattern** (lines 59-76) — add hasher init after file handle opens:
```python
def open(self) -> None:
    """Open file handles for requested formats."""
    if "fasta" in self.formats:
        path = self.outdir / f"{self.prefix}_sequences.fasta"
        self.file_handles["fasta"] = open(path, "w")
        self.output_paths["fasta"] = path
        # NEW: init hasher + counter
        self._hashers["fasta"] = hashlib.sha256()
        self._record_counts["fasta"] = 0

    if "csv" in self.formats:
        path = self.outdir / f"{self.prefix}_metadata.csv"
        self.file_handles["csv"] = open(path, "w")
        self.output_paths["csv"] = path
        self._hashers["csv"] = hashlib.sha256()
        self._record_counts["csv"] = 0

    if "json" in self.formats:
        path = self.outdir / f"{self.prefix}_metadata.json"
        self.file_handles["json"] = open(path, "w")
        self.output_paths["json"] = path
        self._hashers["json"] = hashlib.sha256()
        self._record_counts["json"] = 0
        # Start JSON list (existing)
        self.file_handles["json"].write("[\n")
        # NEW: hash the opening bracket
        self._hashers["json"].update(b"[\n")
```

**`write_record()` FASTA hashing pattern** (lines 81-85) — extend after writing:
```python
# FASTA (existing write + new hash)
if "fasta" in self.file_handles and record.sequence:
    f = self.file_handles["fasta"]
    desc = record.description if record.description else record.title
    f.write(f">{record.accession} {desc}\n")
    f.write(f"{record.sequence}\n")
    # NEW: hash the exact bytes written
    self._hashers["fasta"].update(
        f">{record.accession} {desc}\n{record.sequence}\n".encode("utf-8")
    )
    self._record_counts["fasta"] += 1
```

**`write_record()` CSV hashing pattern** (lines 88-93) — use pre-buffer approach:
```python
# CSV — pre-buffer to StringIO, hash bytes, then write same bytes
if "csv" in self.file_handles:
    f = self.file_handles["csv"]
    data = vars(record)
    df = pd.DataFrame([data])
    import io
    buf = io.StringIO()
    df.to_csv(buf, header=self._is_first_csv_row, index=False)
    csv_str = buf.getvalue()
    self._hashers["csv"].update(csv_str.encode("utf-8"))
    f.write(csv_str)
    self._is_first_csv_row = False
    self._record_counts["csv"] += 1
```

**`write_record()` JSON hashing pattern** (lines 96-105) — extend:
```python
# JSON — hash every write including commas and record data
if "json" in self.file_handles:
    f = self.file_handles["json"]
    if not hasattr(self, "_json_count"):
        self._json_count = 0

    if self._json_count > 0:
        f.write(",\n")
        # NEW: hash the comma+newline separator
        self._hashers["json"].update(b",\n")

    json.dump(vars(record), f, indent=2, default=str)
    # NEW: hash the record JSON bytes (re-serialize to capture exact output)
    import json as _json
    record_bytes = _json.dumps(vars(record), indent=2, default=str).encode("utf-8")
    self._hashers["json"].update(record_bytes)
    self._json_count += 1
    self._record_counts["json"] += 1
```

**`close()` manifest writing pattern** (lines 107-117) — extend after closing bracket:
```python
def close(self) -> None:
    """Close all open file handles and write manifest."""
    if "json" in self.file_handles:
        # End JSON list (existing)
        closing = "\n]"
        self.file_handles["json"].write(closing)
        # NEW: hash the closing bracket
        self._hashers["json"].update(closing.encode("utf-8"))

    # NEW: compute final digests before closing file handles
    self._checksums = {fmt: h.hexdigest() for fmt, h in self._hashers.items()}

    # Close handles (existing)
    for handle in self.file_handles.values():
        handle.close()
    self.file_handles.clear()

    # NEW: write manifest if configured
    self._write_manifest()

    logger.info(f"Streaming export to {self.outdir} complete.")
```

**Manifest writing method** (new, following config/loader.py file I/O patterns):
```python
def _write_manifest(self) -> None:
    """Write manifest.json and manifest-sha256.txt to output directory."""
    if not self._job_name:
        return  # manifest only written for full job runs, not standalone export

    manifest = {
        "manifest_version": "1.0",
        "job_name": self._job_name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config": asdict(self._job_config) if self._job_config else {},
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
                "provider": list(self._databases),  # multi-provider support
            }
            for fmt, p in self.output_paths.items()
        ],
    }

    manifest_path = self.outdir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    # BagIt-compatible companion file (sha256sum -c format)
    lines = []
    for entry in manifest["files"]:
        lines.append(f"{entry['sha256']}  {entry['path']}")
    sha256sum_path = self.outdir / "manifest-sha256.txt"
    sha256sum_path.write_text("\n".join(lines) + "\n")
```

**`__init__` signature extension** (lines 25-50) — add optional params for manifest:
```python
def __init__(
    self,
    outdir: Path,
    prefix: str,
    formats: List[str],
    # NEW params for manifest support
    job_name: str | None = None,
    databases: list[str] | None = None,
    job_config: JobConfig | None = None,
) -> None:
```

**Error handling pattern** (following exporter.py existing patterns) — the exporter currently doesn't have internal error handling. Following the project error handling conventions (CONVENTIONS.md):
```python
# In _write_manifest():
try:
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
except OSError as exc:
    logger.warning(f"Failed to write manifest: {exc}. Export data is still valid.")
    # NOTE: Data files are already on disk. Missing manifest is recoverable.
```

---

### `src/biocurator/core/curator.py` (core/orchestrator, request-response + streaming) — MODIFY

**Analog:** Self — extend existing patterns.

**StreamingExporter instantiation pattern** (lines 151-153) — add manifest params:
```python
# Current (line 151-153):
with StreamingExporter(
    outdir, export_config.prefix, export_config.formats
) as exporter:

# Modified:
with StreamingExporter(
    outdir,
    export_config.prefix,
    export_config.formats,
    job_name=job_config.name,
    databases=job_config.search.databases,
    job_config=job_config,
) as exporter:
```

**Return value pattern** (line 286) — add manifest path to returned dict:
```python
# Current:
return exporter.get_output_files()

# Modified:
output_files = exporter.get_output_files()
output_files["manifest"] = outdir / "manifest.json"
output_files["manifest_sha256"] = outdir / "manifest-sha256.txt"
return output_files
```

---

### `src/biocurator/core/verifier.py` (utility/library, file-I/O) — NEW

**Analog:** `src/biocurator/config/loader.py` (role-match: utility that reads files → returns structured data) + `src/biocurator/utils/logging.py` (module-level pure function pattern)

**Imports pattern** — follow `loader.py` (lines 1-13):
```python
"""Verification Module

Provides library functions for verifying manifest checksums against
files on disk. Phase 4 CLI wraps these with Typer.
"""

import hashlib
import json
from pathlib import Path
from typing import Any

from biocurator.utils.logging import get_logger

logger = get_logger(__name__)
```

**Core function pattern** — follow `ConfigLoader.load()` static method (loader.py lines 14-27) but as a plain function (logging.py pure-function style):
```python
def manifest_verify(manifest_path: Path) -> dict[str, Any]:
    """Verify checksums in manifest against files on disk.

    Parameters
    ----------
    manifest_path : Path
        Path to the manifest.json file.

    Returns
    -------
    dict[str, Any]
        Verification report with keys:
        - manifest_path: str
        - manifest_valid: bool
        - files_checked: int
        - files_matched: int
        - files_missing: int
        - files_corrupted: int
        - results: list[dict] with per-file {path, sha256_expected, sha256_actual, status}
    """
    manifest_path = Path(manifest_path)

    # Load manifest JSON
    try:
        manifest = json.loads(manifest_path.read_text())
        manifest_valid = True
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning(f"Cannot parse manifest: {exc}")
        return {
            "manifest_path": str(manifest_path),
            "manifest_valid": False,
            "files_checked": 0,
            "files_matched": 0,
            "files_missing": 0,
            "files_corrupted": 0,
            "results": [],
        }

    base_dir = manifest_path.parent
    results = []
    files_matched = 0
    files_missing = 0
    files_corrupted = 0

    for file_entry in manifest.get("files", []):
        rel_path = file_entry.get("path", "")
        expected_sha256 = file_entry.get("sha256", "")

        # Resolve path relative to manifest directory (D-03: portable)
        file_path = base_dir / rel_path

        if not file_path.exists():
            results.append({
                "path": rel_path,
                "sha256_expected": expected_sha256,
                "sha256_actual": None,
                "status": "missing",
            })
            files_missing += 1
            continue

        # Re-compute SHA-256 from disk (anti-pattern avoidance: never trust stored checksum)
        h = hashlib.sha256()
        with open(file_path, "rb") as fh:
            for chunk in iter(lambda: fh.read(8192), b""):
                h.update(chunk)
        actual = h.hexdigest()

        if actual == expected_sha256:
            status = "ok"
            files_matched += 1
        else:
            status = "corrupted"
            files_corrupted += 1

        results.append({
            "path": rel_path,
            "sha256_expected": expected_sha256,
            "sha256_actual": actual,
            "status": status,
        })

    return {
        "manifest_path": str(manifest_path),
        "manifest_valid": manifest_valid,
        "files_checked": len(results),
        "files_matched": files_matched,
        "files_missing": files_missing,
        "files_corrupted": files_corrupted,
        "results": results,
    }
```

**Security pattern** — path traversal prevention (from RESEARCH.md security section):
```python
# In manifest_verify(), after reading file_entry["path"]:
rel_path = file_entry.get("path", "")
# Security: reject traversal paths per RESEARCH.md V5 mitigation
if ".." in rel_path or rel_path.startswith("/"):
    logger.warning(f"Skipping suspicious path in manifest: {rel_path}")
    continue
```

---

### `tests/core/test_exporter.py` (test unit/integration, file-I/O) — NEW

**Analog:** `tests/core/test_streaming_curation.py` (exact: same test directory, same file-I/O assertions, same fixture patterns with tmp_path)

**Imports pattern** (from test_streaming_curation.py lines 1-6):
```python
import hashlib
import json
from pathlib import Path
import pytest
from biocurator.core.exporter import StreamingExporter
from biocurator.providers.base import SequenceRecord
from biocurator.config.schema import JobConfig, SearchConfig, FilterConfig, ExportConfig
```

**Fixture pattern** (from test_streaming_curation.py lines 9-19, test_curator.py lines 14-21):
```python
@pytest.fixture
def sample_record():
    return SequenceRecord(
        id="123",
        accession="NC_012345.1",
        title="Test Sequence",
        sequence="ATGCATGC",
        sequence_length=8,
        database="NCBI",
        organism="Test virus",
        downloaded=True,
    )

@pytest.fixture
def sample_job_config(tmp_path):
    return JobConfig(
        name="test-job",
        search=SearchConfig(databases=["ncbi"], organism="Test virus"),
        filter=FilterConfig(),
        export=ExportConfig(
            outdir=str(tmp_path / "results"),
            formats=["fasta", "csv", "json"],
            prefix="test",
        ),
    )
```

**Test structure pattern** (from test_streaming_curation.py lines 22-62):
```python
def test_sha256_fasta_streaming(tmp_path, sample_record, sample_job_config):
    """DI-01: SHA-256 computed for FASTA during streaming export."""
    # Arrange
    exporter = StreamingExporter(
        outdir=tmp_path / "results",
        prefix="test",
        formats=["fasta"],
        job_name="test-job",
        databases=["ncbi"],
        job_config=sample_job_config,
    )
    exporter.open()
    exporter.write_record(sample_record)
    exporter.close()

    # Act — re-read file from disk and compute expected hash
    fasta_path = exporter.output_paths["fasta"]
    actual_on_disk = hashlib.sha256(fasta_path.read_bytes()).hexdigest()

    # Assert — checksum in exporter matches file on disk
    assert exporter._checksums["fasta"] == actual_on_disk
    assert exporter._record_counts["fasta"] == 1


def test_manifest_written_to_outdir(tmp_path, sample_record, sample_job_config):
    """DI-02: manifest.json written to output directory with correct structure."""
    exporter = StreamingExporter(
        outdir=tmp_path / "results",
        prefix="test",
        formats=["fasta"],
        job_name="test-job",
        databases=["ncbi"],
        job_config=sample_job_config,
    )
    exporter.open()
    exporter.write_record(sample_record)
    exporter.close()

    manifest_path = tmp_path / "results" / "manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text())
    assert manifest["manifest_version"] == "1.0"
    assert manifest["job_name"] == "test-job"
    assert manifest["stats"]["total_records"] == 1
    assert len(manifest["files"]) == 1
    assert manifest["files"][0]["sha256"]


def test_sha256sum_companion_file(tmp_path, sample_record, sample_job_config):
    """DI-02: manifest-sha256.txt written with sha256sum -c compatible format."""
    exporter = StreamingExporter(
        outdir=tmp_path / "results",
        prefix="test",
        formats=["fasta"],
        job_name="test-job",
        databases=["ncbi"],
        job_config=sample_job_config,
    )
    exporter.open()
    exporter.write_record(sample_record)
    exporter.close()

    sha256sum_path = tmp_path / "results" / "manifest-sha256.txt"
    assert sha256sum_path.exists()
    content = sha256sum_path.read_text().strip()
    # Format: HASH  FILENAME
    assert "  " in content
    hash_val, filename = content.split("  ", 1)
    assert len(hash_val) == 64  # SHA-256 is 64 hex chars
    assert filename.endswith(".fasta")


def test_manifest_contains_config_snapshot(tmp_path, sample_record, sample_job_config):
    """DI-03: manifest includes config snapshot via dataclasses.asdict()."""
    exporter = StreamingExporter(
        outdir=tmp_path / "results",
        prefix="test",
        formats=["fasta"],
        job_name="test-job",
        databases=["ncbi"],
        job_config=sample_job_config,
    )
    exporter.open()
    exporter.write_record(sample_record)
    exporter.close()

    manifest = json.loads((tmp_path / "results" / "manifest.json").read_text())
    assert "config" in manifest
    assert manifest["config"]["name"] == "test-job"
```

**Error/no-manifest-when-no-job-name test** (from test_curator.py line 93-100 for edge case pattern):
```python
def test_no_manifest_when_no_job_name(tmp_path, sample_record):
    """No manifest written for standalone exports without job metadata."""
    exporter = StreamingExporter(
        outdir=tmp_path / "results",
        prefix="test",
        formats=["fasta"],
    )
    exporter.open()
    exporter.write_record(sample_record)
    exporter.close()

    assert not (tmp_path / "results" / "manifest.json").exists()
    assert not (tmp_path / "results" / "manifest-sha256.txt").exists()
```

---

### `tests/core/test_verifier.py` (test unit, file-I/O) — NEW

**Analog:** `tests/utils/test_logging.py` (exact: simple unit tests for pure functions, direct imports, flat test functions)

**Imports pattern** (from test_logging.py line 1):
```python
import json
import hashlib
import pytest
from pathlib import Path
from biocurator.core.verifier import manifest_verify
```

**Test structure pattern** (from test_logging.py lines 4-24 — flat functions, no fixtures, direct asserts):
```python
def test_verify_all_match(tmp_path):
    """DI-04: manifest_verify() returns ok when files match."""
    # Arrange — create a file + manifest with matching checksum
    test_file = tmp_path / "test.fasta"
    test_content = b">seq1\nATGC\n"
    test_file.write_bytes(test_content)
    expected_sha256 = hashlib.sha256(test_content).hexdigest()

    manifest = {
        "manifest_version": "1.0",
        "job_name": "test",
        "generated_at": "2026-01-01T00:00:00Z",
        "config": {},
        "databases": ["test"],
        "stats": {"total_records": 1, "total_files": 1},
        "files": [
            {
                "path": "test.fasta",
                "format": "fasta",
                "sha256": expected_sha256,
                "size": len(test_content),
                "record_count": 1,
                "provider": ["test"],
            }
        ],
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))

    # Act
    result = manifest_verify(manifest_path)

    # Assert
    assert result["manifest_valid"] is True
    assert result["files_checked"] == 1
    assert result["files_matched"] == 1
    assert result["files_missing"] == 0
    assert result["files_corrupted"] == 0
    assert result["results"][0]["status"] == "ok"


def test_verify_corrupted_detected(tmp_path):
    """DI-04: manifest_verify() returns corrupted when file changed."""
    test_file = tmp_path / "test.fasta"
    test_content = b">seq1\nATGC\n"
    test_file.write_bytes(test_content)

    # Different checksum than actual file
    wrong_sha256 = hashlib.sha256(b"tampered").hexdigest()

    manifest = {
        "manifest_version": "1.0",
        "job_name": "test",
        "generated_at": "2026-01-01T00:00:00Z",
        "config": {},
        "databases": ["test"],
        "stats": {"total_records": 1, "total_files": 1},
        "files": [{"path": "test.fasta", "format": "fasta", "sha256": wrong_sha256}],
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))

    result = manifest_verify(tmp_path / "manifest.json")
    assert result["files_corrupted"] == 1
    assert result["files_matched"] == 0
    assert result["results"][0]["status"] == "corrupted"


def test_verify_file_missing(tmp_path):
    """DI-04: manifest_verify() returns missing when file absent."""
    manifest = {
        "manifest_version": "1.0",
        "job_name": "test",
        "generated_at": "2026-01-01T00:00:00Z",
        "config": {},
        "databases": ["test"],
        "stats": {"total_records": 1, "total_files": 1},
        "files": [{"path": "nonexistent.fasta", "format": "fasta", "sha256": "a" * 64}],
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))

    result = manifest_verify(tmp_path / "manifest.json")
    assert result["files_missing"] == 1
    assert result["results"][0]["status"] == "missing"


def test_verify_invalid_manifest(tmp_path):
    """DI-04: manifest_verify() handles invalid JSON gracefully."""
    (tmp_path / "manifest.json").write_text("not valid json")

    result = manifest_verify(tmp_path / "manifest.json")
    assert result["manifest_valid"] is False
    assert result["files_checked"] == 0
```

---

### `tests/core/test_streaming_curation.py` (test integration, streaming) — MODIFY

**Analog:** Self — extend existing integration test to assert manifest output.

**Pattern to add** (after existing assertions, following test_curator.py lines 66-73 export assertions pattern):
```python
def test_run_job_streaming(tmp_path, mock_sequence):
    outdir = tmp_path / "results"

    job = JobConfig(
        name="test-job",
        search=SearchConfig(databases=["ncbi"], organism="Test virus", max_results=1),
        filter=FilterConfig(min_length=5),
        export=ExportConfig(outdir=str(outdir), formats=["fasta", "csv", "json"], prefix="test")
    )

    curator = Biocurator(email="test@example.com")

    mock_searcher = MagicMock()
    mock_searcher.search.return_value = ["123"]
    mock_searcher.fetch_metadata.return_value = iter([mock_sequence])
    mock_searcher.download.return_value = iter([mock_sequence])

    curator.searchers["ncbi"] = mock_searcher

    results = curator.run_job(job)

    # Existing assertions (keep unchanged)
    assert "fasta" in results
    assert "csv" in results
    assert "json" in results

    # ...

    # NEW Phase 3: assert manifest output
    manifest_path = outdir / "manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text())
    assert manifest["job_name"] == "test-job"
    assert manifest["stats"]["total_records"] == 1

    # NEW Phase 3: assert sha256sum companion
    sha256sum_path = outdir / "manifest-sha256.txt"
    assert sha256sum_path.exists()
```

**New import to add** (top of file):
```python
import json  # add to existing imports
```

---

## Shared Patterns

### Import Style
**Source:** All existing source files
**Apply to:** verifier.py, test_exporter.py, test_verifier.py, modified exporter.py/curator.py
```python
# Absolute imports from biocurator package root
from biocurator.X.Y import Something
# Standard library grouped first, then third-party, then biocurator
from pathlib import Path
import hashlib
from biocurator.utils.logging import get_logger
```

### Logger Pattern
**Source:** `src/biocurator/core/exporter.py` line 19, `src/biocurator/core/curator.py` line 25
**Apply to:** exporter.py (MODIFY), verifier.py (NEW)
```python
from biocurator.utils.logging import get_logger
logger = get_logger(__name__)
# Usage: logger.info(...), logger.warning(...), logger.debug(...), logger.error(...)
```

### Error Handling Pattern
**Source:** `src/biocurator/config/loader.py` lines 20-25, CONVENTIONS.md
**Apply to:** exporter.py (MODIFY — manifest write), verifier.py (NEW — JSON parse, file reads)
```python
# Raise specific exceptions for unrecoverable errors (follows loader.py pattern)
# Log warning for recoverable errors (follows existing exporter.py pattern)
try:
    # operation
except OSError as exc:
    logger.warning(f"Failed to write manifest: {exc}. Export data is still valid.")
```

### Docstring Style
**Source:** `src/biocurator/core/exporter.py` lines 1-10, 25-41
**Apply to:** verifier.py (NEW), all new test functions
```python
"""
Module-level docstring with empty line after title.
=========================

Description.

© Jan Emmanuel Samson (2026-)
"""

def func(...):
    """Brief one-liner for functions.

    Parameters
    ----------
    param : type
        Description.
    """
```

### `__init__.py` Re-export Pattern
**Source:** `src/biocurator/providers/__init__.py` lines 1-27
**Apply to:** `src/biocurator/core/__init__.py` (MODIFY — add verifier export)

The core `__init__.py` is currently empty. Since the project uses `__all__` in other `__init__.py` files, consider adding:
```python
from biocurator.core.verifier import manifest_verify

__all__ = [
    "manifest_verify",
]
```
However, this is non-blocking and at the planner's discretion.

### Test File Structure
**Source:** `tests/core/test_streaming_curation.py`, `tests/utils/test_logging.py`
**Apply to:** test_exporter.py, test_verifier.py, test_streaming_curation.py (MODIFY)

**Common pattern:**
```python
# Top-level imports (stdlib → third-party → biocurator)
import json
from pathlib import Path
import pytest
from biocurator.X.Y import Target

# Fixtures (if needed) with tmp_path from pytest
@pytest.fixture
def fixture_name(tmp_path):
    ...

# Test functions: def test_description_of_behavior():
# Arrange → Act → Assert pattern
def test_export_manifest(tmp_path):
    # Arrange
    ...
    # Act
    ...
    # Assert
    assert ...
```

### tmp_path Pattern for File-Based Tests
**Source:** `tests/core/test_streaming_curation.py` line 22, `tests/core/test_curator.py` line 14
**Apply to:** test_exporter.py, test_verifier.py
```python
def test_something(tmp_path):
    """Use pytest's tmp_path fixture for temporary directories."""
    outdir = tmp_path / "results"
    outdir.mkdir(parents=True, exist_ok=True)
    test_file = tmp_path / "test.fasta"
    test_file.write_text("content")
    # ... test logic with asserts on Path(...).exists(), .read_text(), etc.
```

## No Analog Found

All files in this phase have strong analogs in the existing codebase. No files lack a pattern match.

## Metadata

**Analog search scope:** `src/biocurator/core/`, `src/biocurator/config/`, `src/biocurator/utils/`, `src/biocurator/exceptions.py`, `tests/core/`, `tests/utils/`, `tests/config/`
**Files scanned:** 14
**Pattern extraction date:** 2026-05-25
