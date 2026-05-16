from pathlib import Path
import pytest
from biocurator.config.loader import ConfigLoader
from biocurator.config.schema import GlobalConfig, JobConfig
from biocurator.exceptions import ConfigNotFoundError, InvalidConfigError

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_load_valid_config():
    cfg = ConfigLoader.load(FIXTURES / "valid_config.yaml")
    assert isinstance(cfg, GlobalConfig)
    assert cfg.email == "test@example.com"
    assert len(cfg.jobs) == 2


def test_job_names_are_preserved():
    cfg = ConfigLoader.load(FIXTURES / "valid_config.yaml")
    names = [j.name for j in cfg.jobs]
    assert "covid-genomes" in names
    assert "spike-proteins" in names


def test_search_config_is_parsed():
    cfg = ConfigLoader.load(FIXTURES / "valid_config.yaml")
    covid_job = next(j for j in cfg.jobs if j.name == "covid-genomes")
    assert covid_job.search.databases == ["ncbi"]
    assert covid_job.search.organism == "SARS-CoV-2"
    assert covid_job.search.max_results == 10
    assert "complete genome" in covid_job.search.keywords


def test_filter_config_is_parsed():
    cfg = ConfigLoader.load(FIXTURES / "valid_config.yaml")
    covid_job = next(j for j in cfg.jobs if j.name == "covid-genomes")
    assert covid_job.filter.min_length == 29000
    assert covid_job.filter.quality_threshold == 0.8


def test_export_config_is_parsed():
    cfg = ConfigLoader.load(FIXTURES / "valid_config.yaml")
    covid_job = next(j for j in cfg.jobs if j.name == "covid-genomes")
    assert covid_job.export.outdir == "results/covid"
    assert "fasta" in covid_job.export.formats
    assert covid_job.export.prefix == "covid"


def test_missing_file_raises_config_not_found():
    with pytest.raises(ConfigNotFoundError):
        ConfigLoader.load("nonexistent.yaml")


def test_missing_email_raises_invalid_config():
    with pytest.raises(InvalidConfigError, match="email"):
        ConfigLoader.load(FIXTURES / "missing_email.yaml")


def test_missing_databases_raises_invalid_config():
    with pytest.raises(InvalidConfigError, match="databases"):
        ConfigLoader.load(FIXTURES / "missing_databases.yaml")


def test_empty_job_section_gets_defaults(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        "email: user@example.com\n"
        "jobs:\n"
        "  simple-job:\n"
        "    search:\n"
        "      databases: [ncbi]\n"
        "    filter: {}\n"
        "    export: {}\n"
    )
    cfg = ConfigLoader.load(cfg_file)
    job = cfg.jobs[0]
    assert job.filter.min_length is None
    assert job.export.formats == ["fasta"]
    assert job.export.prefix == "biocurator"
