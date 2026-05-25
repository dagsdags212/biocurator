import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from biocurator.core.curator import Biocurator
from biocurator.config.schema import JobConfig, SearchConfig, FilterConfig, ExportConfig
from biocurator.providers.base import SequenceRecord


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


def test_run_job_streaming(tmp_path, mock_sequence):
    outdir = tmp_path / "results"
    
    job = JobConfig(
        name="test-job",
        search=SearchConfig(databases=["ncbi"], organism="Test virus", max_results=1),
        filter=FilterConfig(min_length=5),
        export=ExportConfig(outdir=str(outdir), formats=["fasta", "csv", "json"], prefix="test")
    )
    
    curator = Biocurator(email="test@example.com")
    
    # Mock NCBI Searcher
    mock_searcher = MagicMock()
    mock_searcher.search.return_value = ["123"]
    mock_searcher.fetch_metadata.return_value = iter([mock_sequence])
    mock_searcher.download.return_value = iter([mock_sequence])
    
    curator.searchers["ncbi"] = mock_searcher
    
    # Run the job
    results = curator.run_job(job)
    
    # Verify outputs
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

    # Manifest assertions
    manifest_path = outdir / "manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text())
    assert manifest["job_name"] == "test-job"
    # total_records sums per-format counts (fasta + csv + json = 3 for 1 record across 3 formats)
    assert manifest["stats"]["total_records"] >= 1

    sha256sum_path = outdir / "manifest-sha256.txt"
    assert sha256sum_path.exists()

    assert "manifest" in results
    assert "manifest_sha256" in results
