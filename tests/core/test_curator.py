import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from biocurator.core.curator import Biocurator
from biocurator.config.schema import JobConfig, SearchConfig, FilterConfig, ExportConfig
from biocurator.providers.base import SequenceRecord


# --------------------------------------------------------------------------
# Fixtures (shared across both legacy and streaming test groups)
# --------------------------------------------------------------------------


@pytest.fixture
def mock_sequence():
    return SequenceRecord(
        id="123",
        accession="NC_012345.1",
        title="Test Sequence",
        sequence="ATGCATGC",
        sequence_length=8,
        database="NCBI",
        downloaded=True
    )


@pytest.fixture
def streaming_job():
    """A job config covering all three export formats."""
    def _make(outdir):
        return JobConfig(
            name="test-job",
            search=SearchConfig(databases=["ncbi"], organism="Test virus", max_results=1),
            filter=FilterConfig(min_length=5),
            export=ExportConfig(outdir=str(outdir), formats=["fasta", "csv", "json"], prefix="test"),
        )
    return _make


@pytest.fixture
def simple_job():
    """A minimal job config with only fasta export."""
    def _make(outdir):
        return JobConfig(
            name="test-job",
            search=SearchConfig(databases=["ncbi"], organism="E. coli", max_results=5),
            filter=FilterConfig(min_length=100),
            export=ExportConfig(outdir=str(outdir / "results"), formats=["fasta"]),
        )
    return _make


@pytest.fixture
def mock_two_seqs():
    """A searcher mock that returns two sequence records."""
    searcher = MagicMock()
    searcher.search.return_value = ["123", "456"]
    searcher.fetch_metadata.return_value = iter([
        SequenceRecord(
            id="123", accession="NC_000001", sequence_length=500,
            organism="E. coli", title="E. coli genome", database="NCBI"
        ),
        SequenceRecord(
            id="456", accession="NC_000002", sequence_length=200,
            organism="E. coli", title="E. coli genome 2", database="NCBI"
        ),
    ])
    searcher.download.return_value = iter([
        SequenceRecord(
            id="123", accession="NC_000001", sequence="ATGC" * 125,
            sequence_length=500, description="E. coli", database="NCBI", downloaded=True
        ),
        SequenceRecord(
            id="456", accession="NC_000002", sequence="ATGC" * 50,
            sequence_length=200, description="E. coli 2", database="NCBI", downloaded=True
        ),
    ])
    return searcher


# --------------------------------------------------------------------------
# Streaming end-to-end (multi-format + manifest)
# --------------------------------------------------------------------------


def test_run_job_streaming(tmp_path, mock_sequence, streaming_job):
    """End-to-end streaming with all 3 export formats and manifest."""
    outdir = tmp_path / "results"
    job = streaming_job(outdir)

    curator = Biocurator(email="test@example.com")

    mock_searcher = MagicMock()
    mock_searcher.search.return_value = ["123"]
    mock_searcher.fetch_metadata.return_value = iter([mock_sequence])
    mock_searcher.download.return_value = iter([mock_sequence])

    curator.searchers["ncbi"] = mock_searcher

    results = curator.run_job(job)

    assert "fasta" in results
    assert "csv" in results
    assert "json" in results

    fasta_path = Path(results["fasta"])
    assert fasta_path.exists()
    content = fasta_path.read_text()
    assert ">NC_012345.1 Test Sequence" in content
    assert "ATGCATGC" in content

    csv_path = Path(results["csv"])
    assert csv_path.exists()
    assert "NC_012345.1" in csv_path.read_text()

    json_path = Path(results["json"])
    assert json_path.exists()
    assert "NC_012345.1" in json_path.read_text()

    manifest_path = outdir / "manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text())
    assert manifest["job_name"] == "test-job"
    assert manifest["stats"]["total_records"] >= 1

    sha256sum_path = outdir / "manifest-sha256.txt"
    assert sha256sum_path.exists()

    assert "manifest" in results
    assert "manifest_sha256" in results


# --------------------------------------------------------------------------
# Individual phase and edge-case behaviours
# --------------------------------------------------------------------------


def test_run_job_calls_search_and_download(tmp_path, simple_job, mock_two_seqs):
    """Verifies all three pipeline methods are invoked."""
    job = simple_job(tmp_path)
    curator = Biocurator(email="test@example.com", outdir=str(tmp_path))
    curator.searchers["ncbi"] = mock_two_seqs

    curator.run_job(job)

    mock_two_seqs.search.assert_called_once()
    mock_two_seqs.fetch_metadata.assert_called_once()
    mock_two_seqs.download.assert_called_once()


def test_run_job_applies_filter(tmp_path, simple_job, mock_two_seqs):
    """Length filter must reduce the set of ids passed to download."""
    job = simple_job(tmp_path)
    job.filter.min_length = 300  # only record 123 (length 500) should pass
    curator = Biocurator(email="test@example.com", outdir=str(tmp_path))
    curator.searchers["ncbi"] = mock_two_seqs

    curator.run_job(job)

    downloaded_ids = mock_two_seqs.download.call_args[0][0]
    assert downloaded_ids == ["123"]


def test_run_job_progress_callback_is_called(tmp_path, simple_job, mock_two_seqs):
    """Progress callback receives each phase."""
    job = simple_job(tmp_path)
    curator = Biocurator(email="test@example.com", outdir=str(tmp_path))
    curator.searchers["ncbi"] = mock_two_seqs

    calls = []
    def callback(phase, current, total):
        calls.append(phase)

    curator.run_job(job, progress_callback=callback)

    assert "search" in calls
    assert "filter" in calls
    assert "download" in calls


def test_run_job_skips_unknown_database(tmp_path, simple_job):
    """An unknown database name should be skipped, not crash."""
    job = simple_job(tmp_path)
    job.search.databases = ["unknown_db"]
    curator = Biocurator(email="test@example.com", outdir=str(tmp_path))

    result = curator.run_job(job)

    # StreamingExporter opens files immediately, so fasta is always in the result
    assert "fasta" in result
