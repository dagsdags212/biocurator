import hashlib
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


def _write_manifest_with_real_files(outdir: Path, job_name: str) -> None:
    """Write manifest.json with real matching files for verify-ok tests."""
    outdir.mkdir(parents=True, exist_ok=True)
    content = b">seq1\nATGC\n"
    fasta = outdir / "alpha_sequences.fasta"
    fasta.write_bytes(content)
    sha256 = hashlib.sha256(content).hexdigest()
    manifest = {
        "manifest_version": "1.0",
        "job_name": job_name,
        "generated_at": "2026-01-01T00:00:00+00:00",
        "config": {},
        "databases": ["ncbi"],
        "stats": {"total_records": 1, "total_files": 1},
        "files": [
            {
                "path": "alpha_sequences.fasta",
                "format": "fasta",
                "sha256": sha256,
                "size": len(content),
                "record_count": 1,
                "provider": ["ncbi"],
            }
        ],
    }
    (outdir / "manifest.json").write_text(json.dumps(manifest))


# ─── Verify-mode tests ─────────────────────────────────────────────────────────


def test_files_verify_ok(tmp_path):
    """All checksums match → exits 0 and shows 'All checksums verified'."""
    alpha_dir = tmp_path / "alpha"
    _write_manifest_with_real_files(alpha_dir, "alpha-job")
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text(
        VALID_CONFIG_TMPL.format(
            alpha_dir=str(alpha_dir), beta_dir=str(tmp_path / "beta")
        )
    )
    result = runner.invoke(app, ["files", "alpha-job", "--verify", "--config", str(cfg)])
    assert result.exit_code == 0
    assert "All checksums verified" in result.output


def test_files_verify_corrupted_exits_1(tmp_path):
    """File on disk does not match manifest checksum → exits 1 with 'corrupted'."""
    alpha_dir = tmp_path / "alpha"
    _write_manifest(alpha_dir, "alpha-job")  # manifest has sha256 = "a"*64 (wrong)
    # Write actual file with different content so checksum mismatches
    (alpha_dir / "alpha_sequences.fasta").write_bytes(b">seq1\nATGC\n")
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text(
        VALID_CONFIG_TMPL.format(
            alpha_dir=str(alpha_dir), beta_dir=str(tmp_path / "beta")
        )
    )
    result = runner.invoke(app, ["files", "alpha-job", "--verify", "--config", str(cfg)])
    assert result.exit_code == 1
    assert "corrupted" in result.output.lower()


def test_files_verify_missing_exits_1(tmp_path):
    """File referenced in manifest is absent on disk → exits 1 with 'missing'."""
    alpha_dir = tmp_path / "alpha"
    alpha_dir.mkdir(parents=True, exist_ok=True)
    # Write a manifest referencing a file that doesn't exist
    manifest = {
        "manifest_version": "1.0",
        "job_name": "alpha-job",
        "generated_at": "2026-01-01T00:00:00+00:00",
        "config": {},
        "databases": ["ncbi"],
        "stats": {"total_records": 1, "total_files": 1},
        "files": [
            {
                "path": "alpha_sequences.fasta",
                "format": "fasta",
                "sha256": "a" * 64,
                "size": 100,
                "record_count": 1,
                "provider": ["ncbi"],
            }
        ],
    }
    (alpha_dir / "manifest.json").write_text(json.dumps(manifest))
    # Intentionally do NOT create alpha_sequences.fasta
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text(
        VALID_CONFIG_TMPL.format(
            alpha_dir=str(alpha_dir), beta_dir=str(tmp_path / "beta")
        )
    )
    result = runner.invoke(app, ["files", "alpha-job", "--verify", "--config", str(cfg)])
    assert result.exit_code == 1
    assert "missing" in result.output.lower()


def test_files_verify_no_manifest_shows_hint(tmp_path):
    """No manifest.json with --verify → exits 0 with hint to run job first."""
    alpha_dir = tmp_path / "alpha"
    alpha_dir.mkdir()
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text(
        VALID_CONFIG_TMPL.format(
            alpha_dir=str(alpha_dir), beta_dir=str(tmp_path / "beta")
        )
    )
    result = runner.invoke(app, ["files", "alpha-job", "--verify", "--config", str(cfg)])
    assert result.exit_code == 0
    assert "run" in result.output.lower()
