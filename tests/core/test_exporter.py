"""
Unit tests for StreamingExporter SHA-256 hashing and manifest generation.

Covers:
  DI-01 — SHA-256 checksum generation during streaming export (FASTA, CSV, JSON)
  DI-02 — Per-job manifest.json and manifest-sha256.txt companion file
  DI-03 — Config snapshot embedded in manifest for provenance tracking
"""

import hashlib
import json
from pathlib import Path

import pytest

from biocurator.config.schema import ExportConfig, FilterConfig, JobConfig, SearchConfig
from biocurator.core.exporter import StreamingExporter
from biocurator.providers.base import SequenceRecord


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_sha256_fasta_streaming(tmp_path, sample_record, sample_job_config):
    """DI-01: Incremental FASTA hash matches disk file hash."""
    outdir = Path(sample_job_config.export.outdir)

    with StreamingExporter(
        outdir,
        sample_job_config.export.prefix,
        ["fasta"],
        job_name=sample_job_config.name,
        databases=sample_job_config.search.databases,
        job_config=sample_job_config,
    ) as exporter:
        exporter.write_record(sample_record)

    fasta_path = outdir / "test_sequences.fasta"
    assert fasta_path.exists()

    disk_hash = hashlib.sha256(fasta_path.read_bytes()).hexdigest()
    assert exporter._checksums["fasta"] == disk_hash
    assert exporter._record_counts["fasta"] == 1


def test_sha256_csv_streaming(tmp_path, sample_record, sample_job_config):
    """DI-01: Incremental CSV hash matches disk file hash."""
    outdir = Path(sample_job_config.export.outdir)

    with StreamingExporter(
        outdir,
        sample_job_config.export.prefix,
        ["csv"],
        job_name=sample_job_config.name,
        databases=sample_job_config.search.databases,
        job_config=sample_job_config,
    ) as exporter:
        exporter.write_record(sample_record)

    csv_path = outdir / "test_metadata.csv"
    assert csv_path.exists()

    disk_hash = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    assert exporter._checksums["csv"] == disk_hash
    assert exporter._record_counts["csv"] == 1


def test_sha256_json_streaming(tmp_path, sample_record, sample_job_config):
    """DI-01: Incremental JSON hash matches disk file hash."""
    outdir = Path(sample_job_config.export.outdir)

    with StreamingExporter(
        outdir,
        sample_job_config.export.prefix,
        ["json"],
        job_name=sample_job_config.name,
        databases=sample_job_config.search.databases,
        job_config=sample_job_config,
    ) as exporter:
        exporter.write_record(sample_record)

    json_path = outdir / "test_metadata.json"
    assert json_path.exists()

    disk_hash = hashlib.sha256(json_path.read_bytes()).hexdigest()
    assert exporter._checksums["json"] == disk_hash
    assert exporter._record_counts["json"] == 1


def test_manifest_written_to_outdir(tmp_path, sample_record, sample_job_config):
    """DI-02: manifest.json exists and contains required top-level keys."""
    outdir = Path(sample_job_config.export.outdir)

    with StreamingExporter(
        outdir,
        sample_job_config.export.prefix,
        ["fasta"],
        job_name=sample_job_config.name,
        databases=sample_job_config.search.databases,
        job_config=sample_job_config,
    ) as exporter:
        exporter.write_record(sample_record)

    manifest_path = outdir / "manifest.json"
    assert manifest_path.exists()

    manifest = json.loads(manifest_path.read_text())
    assert manifest["manifest_version"] == "1.0"
    assert manifest["job_name"] == "test-job"
    assert manifest["stats"]["total_records"] == 1
    assert len(manifest["files"]) == 1
    assert manifest["files"][0]["sha256"]  # non-empty hash string


def test_sha256sum_companion_file(tmp_path, sample_record, sample_job_config):
    """DI-02: manifest-sha256.txt uses double-space format and contains valid 64-hex hash."""
    outdir = Path(sample_job_config.export.outdir)

    with StreamingExporter(
        outdir,
        sample_job_config.export.prefix,
        ["fasta"],
        job_name=sample_job_config.name,
        databases=sample_job_config.search.databases,
        job_config=sample_job_config,
    ) as exporter:
        exporter.write_record(sample_record)

    sha256sum_path = outdir / "manifest-sha256.txt"
    assert sha256sum_path.exists()

    content = sha256sum_path.read_text()
    # BagIt / sha256sum -c compatible: HASH  FILENAME (double-space separator)
    assert "  " in content

    first_line = content.splitlines()[0]
    hash_part, filename_part = first_line.split("  ", 1)
    assert len(hash_part) == 64  # SHA-256 hex digest length
    assert filename_part.endswith(".fasta")


def test_manifest_contains_config_snapshot(tmp_path, sample_record, sample_job_config):
    """DI-03: manifest.json embeds a config snapshot for provenance."""
    outdir = Path(sample_job_config.export.outdir)

    with StreamingExporter(
        outdir,
        sample_job_config.export.prefix,
        ["fasta"],
        job_name=sample_job_config.name,
        databases=sample_job_config.search.databases,
        job_config=sample_job_config,
    ) as exporter:
        exporter.write_record(sample_record)

    manifest = json.loads((outdir / "manifest.json").read_text())
    assert "config" in manifest
    assert manifest["config"]["name"] == "test-job"


def test_no_manifest_when_no_job_name(tmp_path, sample_record):
    """Edge case: exporter without job_name must not produce manifest files."""
    outdir = tmp_path / "standalone"

    with StreamingExporter(outdir, "test", ["fasta"]) as exporter:
        exporter.write_record(sample_record)

    assert not (outdir / "manifest.json").exists()
    assert not (outdir / "manifest-sha256.txt").exists()


def test_record_counts_accurate(tmp_path, sample_record, sample_job_config):
    """DI-03: _record_counts matches the actual number of records written."""
    outdir = Path(sample_job_config.export.outdir)

    with StreamingExporter(
        outdir,
        sample_job_config.export.prefix,
        ["fasta"],
        job_name=sample_job_config.name,
        databases=sample_job_config.search.databases,
        job_config=sample_job_config,
    ) as exporter:
        exporter.write_record(sample_record)
        exporter.write_record(sample_record)
        exporter.write_record(sample_record)

    assert exporter._record_counts["fasta"] == 3
