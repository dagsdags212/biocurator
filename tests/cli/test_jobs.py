from typer.testing import CliRunner
from biocurator.cli.main import app

runner = CliRunner()

VALID_CONFIG = """\
email: test@example.com
jobs:
  alpha-job:
    search:
      databases: [ncbi]
      organism: "E. coli"
      max_results: 10
    filter: {}
    export:
      outdir: results
      formats: [fasta]
      prefix: alpha
  beta-job:
    search:
      databases: [uniprot]
      max_results: 5
    filter: {}
    export:
      outdir: results2
      formats: [csv, json]
      prefix: beta
"""


def test_jobs_default_config_not_found():
    """biocurator jobs with a nonexistent config path exits non-zero."""
    result = runner.invoke(app, ["jobs", "--config", "nonexistent_file_xyz.yaml"])
    assert result.exit_code != 0
    assert "not found" in result.output.lower()


def test_jobs_explicit_config_not_found():
    """biocurator jobs --config nonexistent exits non-zero with 'not found' message."""
    result = runner.invoke(app, ["jobs", "--config", "nonexistent.yaml"])
    assert result.exit_code != 0
    assert "not found" in result.output.lower()


def test_jobs_lists_all_jobs(tmp_path):
    """biocurator jobs --config {path} exits 0 and displays all job names."""
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text(VALID_CONFIG)
    result = runner.invoke(app, ["jobs", "--config", str(cfg)])
    assert result.exit_code == 0
    assert "alpha-job" in result.output
    assert "beta-job" in result.output


def test_jobs_shows_databases(tmp_path):
    """biocurator jobs shows database names for each job."""
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text(VALID_CONFIG)
    result = runner.invoke(app, ["jobs", "--config", str(cfg)])
    assert result.exit_code == 0
    assert "ncbi" in result.output
    assert "uniprot" in result.output


def test_jobs_shows_job_count(tmp_path):
    """biocurator jobs footer shows correct job count."""
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text(VALID_CONFIG)
    result = runner.invoke(app, ["jobs", "--config", str(cfg)])
    assert result.exit_code == 0
    assert "2 job(s)" in result.output
