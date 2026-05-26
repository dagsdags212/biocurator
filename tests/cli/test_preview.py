from pathlib import Path
from unittest.mock import MagicMock, patch
from typer.testing import CliRunner
from biocurator.cli.main import app

runner = CliRunner()


def test_preview_curator_receives_global_breaker(tmp_path):
    """D-01: preview command passes global_retry and global_breaker to Biocurator constructor."""
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

    with patch("biocurator.cli.commands.preview.Biocurator") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.searchers = {"ncbi": MagicMock()}
        mock_cls.return_value = mock_instance

        result = runner.invoke(app, ["preview", "test-job", "--config", str(cfg)])

    assert result.exit_code == 0, f"Command failed: {result.output}"
    assert mock_cls.call_args is not None, "Biocurator() was not called"
    assert "global_breaker" in mock_cls.call_args[1], (
        "Biocurator() was not called with global_breaker keyword argument"
    )
    breaker_arg = mock_cls.call_args[1]["global_breaker"]
    assert breaker_arg is not None, (
        "global_breaker should not be None when config has breaker block"
    )
    assert breaker_arg.fail_max == 3, f"Expected fail_max=3, got {breaker_arg.fail_max}"
    assert "global_retry" in mock_cls.call_args[1], (
        "Biocurator() was not called with global_retry keyword argument"
    )
