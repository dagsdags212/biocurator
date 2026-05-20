from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from biocurator.config.schema import (
    ExportConfig,
    FilterConfig,
    JobConfig,
    SearchConfig,
)
from biocurator.core.curator import Biocurator
from biocurator.providers.base import SequenceRecord


@pytest.fixture
def job_config(tmp_path):
    return JobConfig(
        name="test-job",
        search=SearchConfig(databases=["ncbi"], organism="E. coli", max_results=5),
        filter=FilterConfig(min_length=100),
        export=ExportConfig(outdir=str(tmp_path / "results"), formats=["fasta"]),
    )


@pytest.fixture
def mock_ncbi_searcher():
    searcher = MagicMock()
    searcher.search.return_value = ["123", "456"]
    searcher.fetch_metadata.return_value = iter([
        SequenceRecord(id="123", accession="NC_000001", sequence_length=500, organism="E. coli",
                       title="E. coli genome", database="NCBI"),
        SequenceRecord(id="456", accession="NC_000002", sequence_length=200, organism="E. coli",
                       title="E. coli genome 2", database="NCBI"),
    ])
    searcher.download.return_value = iter([
        SequenceRecord(id="123", accession="NC_000001", sequence="ATGC" * 125,
                       sequence_length=500, description="E. coli", database="NCBI", downloaded=True),
        SequenceRecord(id="456", accession="NC_000002", sequence="ATGC" * 50,
                       sequence_length=200, description="E. coli 2", database="NCBI", downloaded=True),
    ])
    return searcher


def test_run_job_calls_search_and_download(job_config, mock_ncbi_searcher, tmp_path):
    curator = Biocurator(email="test@example.com", outdir=str(tmp_path))
    curator.searchers["ncbi"] = mock_ncbi_searcher

    curator.run_job(job_config)

    mock_ncbi_searcher.search.assert_called_once()
    mock_ncbi_searcher.fetch_metadata.assert_called_once()
    mock_ncbi_searcher.download.assert_called_once()


def test_run_job_applies_filter(job_config, mock_ncbi_searcher, tmp_path):
    job_config.filter.min_length = 300  # only "123" with length 500 should pass
    curator = Biocurator(email="test@example.com", outdir=str(tmp_path))
    curator.searchers["ncbi"] = mock_ncbi_searcher

    curator.run_job(job_config)

    # Only 1 id should have been passed to download
    downloaded_ids = mock_ncbi_searcher.download.call_args[0][0]
    assert downloaded_ids == ["123"]


def test_run_job_exports_fasta(job_config, mock_ncbi_searcher, tmp_path):
    curator = Biocurator(email="test@example.com", outdir=str(tmp_path))
    curator.searchers["ncbi"] = mock_ncbi_searcher

    result = curator.run_job(job_config)

    fasta_files = list(Path(job_config.export.outdir).glob("*.fasta"))
    assert len(fasta_files) == 1


def test_run_job_progress_callback_is_called(job_config, mock_ncbi_searcher, tmp_path):
    curator = Biocurator(email="test@example.com", outdir=str(tmp_path))
    curator.searchers["ncbi"] = mock_ncbi_searcher

    calls = []
    def callback(phase, current, total):
        calls.append(phase)

    curator.run_job(job_config, progress_callback=callback)

    assert "search" in calls
    assert "filter" in calls
    assert "download" in calls
    # Note: 'export' is no longer a separate phase in run_job reporting, 
    # it happens during download streaming.


def test_run_job_skips_unknown_database(job_config, tmp_path):
    job_config.search.databases = ["unknown_db"]
    curator = Biocurator(email="test@example.com", outdir=str(tmp_path))

    result = curator.run_job(job_config)
    # result should contain the paths to files (even if empty) because StreamingExporter 
    # opens them immediately in the 'with' block.
    assert "fasta" in result
