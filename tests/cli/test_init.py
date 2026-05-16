from pathlib import Path
from typer.testing import CliRunner
from biocurator.cli.main import app

runner = CliRunner()


def test_init_prints_to_stdout_by_default():
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    assert "email:" in result.output
    assert "jobs:" in result.output


def test_init_writes_file_when_output_given(tmp_path):
    out = tmp_path / "config.yaml"
    result = runner.invoke(app, ["init", "--output", str(out)])
    assert result.exit_code == 0
    assert out.exists()
    content = out.read_text()
    assert "email:" in content
    assert "jobs:" in content


def test_init_advanced_template_includes_all_fields():
    result = runner.invoke(app, ["init", "--template", "advanced"])
    assert result.exit_code == 0
    assert "exclude_terms" in result.output
    assert "quality_threshold" in result.output
    assert "date_range" in result.output


def test_init_basic_template_is_concise():
    result = runner.invoke(app, ["init", "--template", "basic"])
    assert result.exit_code == 0
    assert "email:" in result.output
    # basic template should not include optional advanced fields
    assert "taxonomy_filter" not in result.output
