import pytest
from biocurator.providers.base import (
    SearchCriteria,
    DatabaseConfig,
    DatabaseSearcher,
)
from abc import ABC
from pathlib import Path
from typing import Any


def test_search_criteria_defaults():
    c = SearchCriteria()
    assert c.sequence_type == "nucleotide"
    assert c.max_results == 100
    assert c.keywords == []


def test_search_criteria_exclude_terms_defaults_to_empty_list():
    c = SearchCriteria()
    assert c.exclude_terms == []


def test_search_criteria_optional_fields_are_none_by_default():
    c = SearchCriteria()
    for field in ("organism", "location", "min_length", "max_length",
                  "start_date", "end_date", "taxonomy_filter", "quality_threshold"):
        assert getattr(c, field) is None


def test_search_criteria_all_fields_settable():
    c = SearchCriteria(
        organism="Homo sapiens",
        sequence_type="protein",
        keywords=["kinase"],
        location="Europe",
        min_length=50,
        max_length=1000,
        start_date="2020/01/01",
        end_date="2024/12/31",
        max_results=50,
        exclude_terms=["predicted"],
        taxonomy_filter="Mammalia",
        quality_threshold=0.9,
    )
    assert c.organism == "Homo sapiens"
    assert c.sequence_type == "protein"
    assert c.max_results == 50
    assert c.quality_threshold == 0.9


def test_database_config_required_name():
    cfg = DatabaseConfig(name="test")
    assert cfg.name == "test"
    assert cfg.rate_limit == 0.3


def test_database_config_defaults():
    cfg = DatabaseConfig(name="db")
    assert cfg.base_url is None
    assert cfg.api_key is None
    assert cfg.batch_size == 20
    assert cfg.timeout == 30


def test_database_config_all_fields_settable():
    cfg = DatabaseConfig(
        name="custom",
        base_url="https://example.com",
        api_key="secret",
        rate_limit=1.0,
        batch_size=50,
        timeout=60,
    )
    assert cfg.base_url == "https://example.com"
    assert cfg.api_key == "secret"
    assert cfg.batch_size == 50


def test_database_searcher_is_abstract():
    assert issubclass(DatabaseSearcher, ABC)
    for method in ("build_query", "search", "fetch_metadata", "download"):
        assert method in DatabaseSearcher.__abstractmethods__


def test_database_searcher_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        DatabaseSearcher(DatabaseConfig(name="x"), "a@b.com")  # type: ignore[abstract]


def test_database_searcher_concrete_subclass_exposes_session():
    class _Concrete(DatabaseSearcher):
        def build_query(self, criteria: SearchCriteria) -> str:
            return ""
        def search(self, criteria: SearchCriteria) -> list[str]:
            return []
        def fetch_metadata(self, ids: list[str]) -> list[dict[str, Any]]:
            return []
        def download(self, ids: list[str], outdir: Path) -> list[dict[str, Any]]:
            return []

    s = _Concrete(DatabaseConfig(name="x"), "user@example.com")
    assert s.email == "user@example.com"
    assert s.config.name == "x"
    assert s.session is not None
