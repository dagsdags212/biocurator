import json
from pathlib import Path
from typer.testing import CliRunner
from biocurator.cli.main import app

runner = CliRunner()

VALID_CONFIG_TMPL = """\
email: test@example.com
jobs:
  alpha-job:
    search:
      databases: [ncbi]
      max_results: 5
    filter: {{}}
    export:
      outdir: {alpha_dir}
      formats: [fasta]
      prefix: alpha
  beta-job:
    search:
      databases: [uniprot]
      max_results: 5
    filter: {{}}
    export:
      outdir: {beta_dir}
      formats: [csv]
      prefix: beta
"""


def _write_manifest(outdir: Path, job_name: str, files_count: int = 1) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "manifest_version": "1.0",
        "job_name": job_name,
        "generated_at": "2026-01-01T00:00:00+00:00",
        "config": {},
        "databases": ["ncbi"],
        "stats": {"total_records": 10, "total_files": files_count},
        "files": [
            {
                "path": "alpha_sequences.fasta",
                "format": "fasta",
                "sha256": "a" * 64,
                "size": 2048,
                "record_count": 10,
                "provider": ["ncbi"],
            }
        ],
    }
    (outdir / "manifest.json").write_text(json.dumps(manifest))


# ─── List-mode tests ───────────────────────────────────────────────────────────


def test_files_no_manifest_shows_run_hint(tmp_path):
    """With no manifest.json the command exits 0 and suggests biocurator run."""
    alpha_dir = tmp_path / "alpha"
    alpha_dir.mkdir()
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text(
        VALID_CONFIG_TMPL.format(
            alpha_dir=str(alpha_dir), beta_dir=str(tmp_path / "beta")
        )
    )
    result = runner.invoke(app, ["files", "alpha-job", "--config", str(cfg)])
    assert result.exit_code == 0
    assert "run" in result.output.lower()


def test_files_shows_job_files(tmp_path):
    """With manifest.json present, file entry appears in the output table."""
    alpha_dir = tmp_path / "alpha"
    _write_manifest(alpha_dir, "alpha-job")
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text(
        VALID_CONFIG_TMPL.format(
            alpha_dir=str(alpha_dir), beta_dir=str(tmp_path / "beta")
        )
    )
    result = runner.invoke(app, ["files", "alpha-job", "--config", str(cfg)])
    assert result.exit_code == 0
    assert "alpha_sequences.fasta" in result.output


def test_files_unknown_job_exits_error(tmp_path):
    """Requesting a job name not in config exits non-zero with 'Unknown job'."""
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text(
        VALID_CONFIG_TMPL.format(
            alpha_dir=str(tmp_path / "alpha"), beta_dir=str(tmp_path / "beta")
        )
    )
    result = runner.invoke(app, ["files", "unknown-job", "--config", str(cfg)])
    assert result.exit_code != 0
    assert "Unknown job" in result.output


def test_files_no_job_name_shows_all_jobs(tmp_path):
    """Omitting job_name shows a summary row for every job."""
    alpha_dir = tmp_path / "alpha"
    _write_manifest(alpha_dir, "alpha-job")
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text(
        VALID_CONFIG_TMPL.format(
            alpha_dir=str(alpha_dir), beta_dir=str(tmp_path / "beta")
        )
    )
    result = runner.invoke(app, ["files", "--config", str(cfg)])
    assert result.exit_code == 0
    assert "alpha-job" in result.output
    assert "beta-job" in result.output


def test_files_no_job_name_no_data_shows_hint(tmp_path):
    """Omitting job_name with no manifests shows a helpful hint to run jobs."""
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text(
        VALID_CONFIG_TMPL.format(
            alpha_dir=str(tmp_path / "alpha"), beta_dir=str(tmp_path / "beta")
        )
    )
    result = runner.invoke(app, ["files", "--config", str(cfg)])
    assert result.exit_code == 0
    assert "run" in result.output.lower()
