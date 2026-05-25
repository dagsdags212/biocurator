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


def test_run_check_with_all_providers_up(tmp_path):
    """--check with all providers UP should proceed to job execution."""
    cfg = tmp_path / "config.yaml"
    cfg.write_text(VALID_CONFIG.format(outdir=str(tmp_path / "results")))

    with patch("biocurator.cli.commands.run.Biocurator") as mock_cls:
        mock_instance = MagicMock()
        # Simulate all providers reachable
        mock_instance.get_health_status.return_value = [
            {
                "provider": "ncbi",
                "status": "UP",
                "response_time_ms": 150.0,
                "breaker_state": "closed",
                "error": None,
            },
        ]
        mock_instance.run_job.return_value = {"fasta": tmp_path / "out.fasta"}
        mock_cls.return_value = mock_instance

        result = runner.invoke(app, ["run", str(cfg), "--check"])

    assert result.exit_code == 0
    # Should have called run_job (proceeded after healthy check)
    assert mock_instance.run_job.call_count == 1


def test_run_check_with_provider_down_prompts_and_user_aborts(tmp_path):
    """--check with DOWN provider — user says no, exits with error."""
    cfg = tmp_path / "config.yaml"
    cfg.write_text(VALID_CONFIG.format(outdir=str(tmp_path / "results")))

    with patch("biocurator.cli.commands.run.Biocurator") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.get_health_status.return_value = [
            {
                "provider": "ncbi",
                "status": "DOWN",
                "response_time_ms": 5000.0,
                "breaker_state": "open",
                "error": "Timeout",
            },
        ]
        mock_cls.return_value = mock_instance

        result = runner.invoke(app, ["run", str(cfg), "--check"], input="n\n")

    assert result.exit_code != 0
    assert mock_instance.run_job.call_count == 0


def test_run_check_with_provider_down_user_proceeds(tmp_path):
    """--check with DOWN provider — user says yes, runs job anyway."""
    cfg = tmp_path / "config.yaml"
    cfg.write_text(VALID_CONFIG.format(outdir=str(tmp_path / "results")))

    with patch("biocurator.cli.commands.run.Biocurator") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.get_health_status.return_value = [
            {
                "provider": "ncbi",
                "status": "DOWN",
                "response_time_ms": 5000.0,
                "breaker_state": "open",
                "error": "Timeout",
            },
        ]
        mock_instance.run_job.return_value = {"fasta": tmp_path / "out.fasta"}
        mock_cls.return_value = mock_instance

        result = runner.invoke(app, ["run", str(cfg), "--check"], input="y\n")

    assert result.exit_code == 0
    assert mock_instance.run_job.call_count == 1


def test_run_main_curator_receives_global_breaker(tmp_path):
    """BREAK-01: main curator (non-check path) receives global_breaker from config."""
    config_with_breaker = """\
email: test@example.com
breaker:
  fail_max: 3
  recovery_timeout: 30

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
""".format(outdir=str(tmp_path / "results"))

    cfg = tmp_path / "config.yaml"
    cfg.write_text(config_with_breaker)

    with patch("biocurator.cli.commands.run.Biocurator") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.run_job.return_value = {"fasta": tmp_path / "out.fasta"}
        mock_cls.return_value = mock_instance

        result = runner.invoke(app, ["run", str(cfg)])

    assert result.exit_code == 0
    # Verify the main curator received global_breaker kwarg
    assert mock_cls.call_args is not None
    assert "global_breaker" in mock_cls.call_args[1], (
        "Biocurator() was not called with global_breaker keyword argument"
    )
    breaker_arg = mock_cls.call_args[1]["global_breaker"]
    assert breaker_arg is not None, (
        "global_breaker should not be None when config has breaker block"
    )
    assert breaker_arg.fail_max == 3, f"Expected fail_max=3, got {breaker_arg.fail_max}"


def test_run_no_check_skips_preflight(tmp_path):
    """--no-check skips pre-flight even if config has preflight_check: true."""
    config_with_pf = """\
email: test@example.com

jobs:
  test-job:
    search:
      databases: [ncbi]
      organism: "E. coli"
      max_results: 5
      preflight_check: true
    filter: {{}}
    export:
      outdir: {outdir}
      formats: [fasta]
      prefix: test
""".format(outdir=str(tmp_path / "results"))

    cfg = tmp_path / "config.yaml"
    cfg.write_text(config_with_pf)

    with patch("biocurator.cli.commands.run.Biocurator") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.run_job.return_value = {}
        mock_cls.return_value = mock_instance

        result = runner.invoke(app, ["run", str(cfg), "--no-check"])

    assert result.exit_code == 0
    # get_health_status should never be called because --no-check bypasses it
    mock_instance.get_health_status.assert_not_called()
