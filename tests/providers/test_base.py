from biocurator.providers.base import (
    SearchCriteria,
    DatabaseConfig,
    DatabaseSearcher,
)
from abc import ABC
from pathlib import Path


def test_search_criteria_defaults():
    c = SearchCriteria()
    assert c.sequence_type == "nucleotide"
    assert c.max_results == 100
    assert c.keywords == []


def test_database_config_required_name():
    cfg = DatabaseConfig(name="test")
    assert cfg.name == "test"
    assert cfg.rate_limit == 0.3


def test_database_searcher_is_abstract():
    assert issubclass(DatabaseSearcher, ABC)
    # Must have the four abstract methods
    for method in ("build_query", "search", "fetch_metadata", "download"):
        assert method in DatabaseSearcher.__abstractmethods__
