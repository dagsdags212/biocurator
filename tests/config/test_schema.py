from dataclasses import fields
from biocurator.config.schema import (
    SearchConfig,
    FilterConfig,
    ExportConfig,
    JobConfig,
    GlobalConfig,
    BreakerConfig,
)


def test_search_config_requires_databases():
    cfg = SearchConfig(databases=["ncbi"])
    assert cfg.databases == ["ncbi"]


def test_search_config_defaults():
    cfg = SearchConfig(databases=["ncbi"])
    assert cfg.organism is None
    assert cfg.sequence_type == "nucleotide"
    assert cfg.keywords == []
    assert cfg.max_results == 100
    assert cfg.date_range is None
    assert cfg.exclude_terms == []
    assert cfg.location is None
    assert cfg.taxonomy_filter is None


def test_filter_config_defaults():
    cfg = FilterConfig()
    assert cfg.min_length is None
    assert cfg.max_length is None
    assert cfg.exclude_terms == []
    assert cfg.quality_threshold is None


def test_export_config_defaults():
    cfg = ExportConfig()
    assert cfg.outdir == "results"
    assert cfg.formats == ["fasta"]
    assert cfg.prefix == "biocurator"


def test_job_config_holds_all_phases():
    job = JobConfig(
        name="my-job",
        search=SearchConfig(databases=["ncbi"]),
        filter=FilterConfig(min_length=1000),
        export=ExportConfig(outdir="out"),
    )
    assert job.name == "my-job"
    assert job.search.databases == ["ncbi"]
    assert job.filter.min_length == 1000
    assert job.export.outdir == "out"


def test_global_config_holds_jobs():
    jobs = [
        JobConfig(
            name="job1",
            search=SearchConfig(databases=["ncbi"]),
            filter=FilterConfig(),
            export=ExportConfig(),
        )
    ]
    cfg = GlobalConfig(email="test@example.com", jobs=jobs)
    assert cfg.email == "test@example.com"
    assert len(cfg.jobs) == 1
    assert cfg.jobs[0].name == "job1"


def test_search_config_preflight_check_defaults_false():
    """Existing behavior: preflight_check defaults to False for backward compat."""
    cfg = SearchConfig(databases=["ncbi"])
    assert cfg.preflight_check == False
    assert cfg.preflight_check is not None  # not None, plain bool


def test_search_config_preflight_check_explicit():
    """Explicit preflight_check: True is stored correctly."""
    cfg = SearchConfig(databases=["ncbi"], preflight_check=True)
    assert cfg.preflight_check == True
    cfg2 = SearchConfig(databases=["ncbi"], preflight_check=False)
    assert cfg2.preflight_check == False


def test_breaker_config_defaults():
    """BreakerConfig().resolve() returns pybreaker default fallbacks."""
    cfg = BreakerConfig().resolve()
    assert cfg.fail_max == 5
    assert cfg.recovery_timeout == 60
    assert cfg.half_open_max_successes == 1


def test_breaker_config_defaults_classmethod():
    """BreakerConfig.defaults() matches BreakerConfig().resolve()."""
    assert BreakerConfig.defaults() == BreakerConfig().resolve()


def test_breaker_config_from_dict_full():
    """BreakerConfig.from_dict() parses all fields from YAML dict."""
    cfg = BreakerConfig.from_dict(
        {
            "fail_max": 3,
            "recovery_timeout": 30,
            "half_open_max_successes": 2,
        }
    )
    assert cfg.fail_max == 3
    assert cfg.recovery_timeout == 30
    assert cfg.half_open_max_successes == 2


def test_breaker_config_from_dict_none():
    """BreakerConfig.from_dict(None) returns None."""
    assert BreakerConfig.from_dict(None) is None


def test_breaker_config_from_dict_empty():
    """BreakerConfig.from_dict({}) returns BreakerConfig with all None fields."""
    cfg = BreakerConfig.from_dict({})
    assert cfg.fail_max is None
    assert cfg.recovery_timeout is None
    assert cfg.half_open_max_successes is None


def test_breaker_config_resolve_with_defaults():
    """BreakerConfig.resolve() merge priority: per-db > global > pybreaker defaults."""
    per_db = BreakerConfig(fail_max=3, half_open_max_successes=2)
    global_defaults = BreakerConfig(
        fail_max=5, recovery_timeout=45, half_open_max_successes=1
    )
    resolved = per_db.resolve(global_defaults)
    assert resolved.fail_max == 3  # per-db overrides global
    assert resolved.recovery_timeout == 45  # falls back to global (per-db is None)
    assert resolved.half_open_max_successes == 2  # per-db overrides global


def test_breaker_config_resolve_partial_override():
    """Partial BreakerConfig resolution falls back to pybreaker defaults."""
    cfg = BreakerConfig(recovery_timeout=30).resolve()
    assert cfg.recovery_timeout == 30  # explicit value kept
    assert cfg.fail_max == 5  # fell back to pybreaker default
    assert cfg.half_open_max_successes == 1  # fell back to pybreaker default
