from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from typer.testing import CliRunner
from biocurator.cli.main import app

runner = CliRunner()

VALID_CONFIG = """\
email: test@example.com

jobs:
  test-job:
    search:
      databases: [ncbi]
      organism: "E. coli"
      max_results: 5
    filter: {{}}
    export:
      outdir: {outdir}
      formats: [fasta]
      prefix: test
"""


def test_run_missing_config_exits_with_error():
    result = runner.invoke(app, ["run", "nonexistent.yaml"])
    assert result.exit_code != 0
    assert "not found" in result.output.lower() or result.exit_code == 1


def test_run_dry_run_does_not_download(tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(VALID_CONFIG.format(outdir=str(tmp_path / "results")))

    with patch("biocurator.cli.commands.run.Biocurator") as mock_cls:
        result = runner.invoke(app, ["run", str(cfg), "--dry-run"])

    assert result.exit_code == 0
    mock_cls.return_value.run_job.assert_not_called()


def test_run_executes_all_jobs(tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(VALID_CONFIG.format(outdir=str(tmp_path / "results")))

    with patch("biocurator.cli.commands.run.Biocurator") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.run_job.return_value = {"fasta": tmp_path / "out.fasta"}
        mock_cls.return_value = mock_instance

        result = runner.invoke(app, ["run", str(cfg)])

    assert result.exit_code == 0
    assert mock_instance.run_job.call_count == 1


def test_run_filters_to_selected_jobs(tmp_path):
    multi_config = """\
email: test@example.com
jobs:
  job-a:
    search:
      databases: [ncbi]
    filter: {{}}
    export:
      outdir: {outdir}
      formats: [fasta]
      prefix: a
  job-b:
    search:
      databases: [uniprot]
    filter: {{}}
    export:
      outdir: {outdir}
      formats: [fasta]
      prefix: b
""".format(outdir=str(tmp_path / "results"))

    cfg = tmp_path / "config.yaml"
    cfg.write_text(multi_config)

    with patch("biocurator.cli.commands.run.Biocurator") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.run_job.return_value = {}
        mock_cls.return_value = mock_instance

        result = runner.invoke(app, ["run", str(cfg), "--jobs", "job-a"])

    assert result.exit_code == 0
    assert mock_instance.run_job.call_count == 1
    called_job = mock_instance.run_job.call_args[0][0]
    assert called_job.name == "job-a"


def test_run_unknown_job_name_exits_with_error(tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(VALID_CONFIG.format(outdir=str(tmp_path / "results")))

    result = runner.invoke(app, ["run", str(cfg), "--jobs", "nonexistent"])
    assert result.exit_code != 0
