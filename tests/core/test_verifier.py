import hashlib
import json
import pytest
from pathlib import Path

from biocurator.core.verifier import manifest_verify


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


def test_verify_path_traversal_rejected(tmp_path):
    """Security: manifest_verify() skips path traversal entries."""
    # Create a valid file (not at the traversal path)
    (tmp_path / "safe.fasta").write_bytes(b">seq1\nATGC\n")

    manifest = {
        "manifest_version": "1.0",
        "job_name": "test",
        "generated_at": "2026-01-01T00:00:00Z",
        "config": {},
        "databases": ["test"],
        "stats": {"total_records": 1, "total_files": 1},
        "files": [{"path": "../etc/passwd", "format": "fasta", "sha256": "a" * 64}],
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))

    result = manifest_verify(tmp_path / "manifest.json")
    # Traversal entry is skipped — not counted in files_checked
    assert result["files_checked"] == 0


def test_verify_mixed_results(tmp_path):
    """DI-04: manifest_verify() correctly handles multiple files with mixed outcomes."""
    # File 1: content matches manifest checksum
    good_content = b">seq1\nATGC\n"
    (tmp_path / "good.fasta").write_bytes(good_content)
    good_sha256 = hashlib.sha256(good_content).hexdigest()

    # File 2: content does not match manifest checksum (corrupted)
    bad_content = b">seq2\nTTTT\n"
    (tmp_path / "bad.fasta").write_bytes(bad_content)
    wrong_sha256 = hashlib.sha256(b"original_content").hexdigest()

    manifest = {
        "manifest_version": "1.0",
        "job_name": "test",
        "generated_at": "2026-01-01T00:00:00Z",
        "config": {},
        "databases": ["test"],
        "stats": {"total_records": 2, "total_files": 2},
        "files": [
            {"path": "good.fasta", "format": "fasta", "sha256": good_sha256},
            {"path": "bad.fasta", "format": "fasta", "sha256": wrong_sha256},
        ],
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))

    result = manifest_verify(tmp_path / "manifest.json")
    assert result["files_checked"] == 2
    assert result["files_matched"] == 1
    assert result["files_corrupted"] == 1

    statuses = {r["path"]: r["status"] for r in result["results"]}
    assert statuses["good.fasta"] == "ok"
    assert statuses["bad.fasta"] == "corrupted"
