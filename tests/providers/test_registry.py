import pytest
from pathlib import Path
from typing import Any
from biocurator.providers.base import DatabaseSearcher, SearchCriteria, DatabaseConfig
from biocurator.providers.registry import ProviderRegistry


class _FakeSearcher(DatabaseSearcher):
    def build_query(self, criteria: SearchCriteria) -> str:
        return "fake_query"

    def search(self, criteria: SearchCriteria) -> list[str]:
        return []

    def fetch_metadata(self, ids: list[str]) -> list[dict[str, Any]]:
        return []

    def download(self, ids: list[str], outdir: Path) -> list[dict[str, Any]]:
        return []


@pytest.fixture(autouse=True)
def clean_registry():
    """Isolate registry state between tests."""
    original = dict(ProviderRegistry._registry)
    yield
    ProviderRegistry._registry.clear()
    ProviderRegistry._registry.update(original)


def test_register_and_get():
    ProviderRegistry.register("fake", _FakeSearcher)
    cfg = DatabaseConfig(name="fake")
    searcher = ProviderRegistry.get("fake", cfg, "test@example.com")
    assert isinstance(searcher, _FakeSearcher)


def test_available_lists_registered_names():
    ProviderRegistry.register("fake", _FakeSearcher)
    assert "fake" in ProviderRegistry.available()


def test_get_unknown_provider_raises():
    with pytest.raises(KeyError, match="unknown_db"):
        ProviderRegistry.get("unknown_db", DatabaseConfig(name="x"), "a@b.com")


def test_available_returns_list():
    assert isinstance(ProviderRegistry.available(), list)


def test_register_multiple_providers():
    class _AnotherSearcher(_FakeSearcher):
        pass

    ProviderRegistry.register("fake", _FakeSearcher)
    ProviderRegistry.register("another", _AnotherSearcher)
    available = ProviderRegistry.available()
    assert "fake" in available
    assert "another" in available


def test_register_overwrites_existing_name():
    class _ReplacementSearcher(_FakeSearcher):
        pass

    ProviderRegistry.register("fake", _FakeSearcher)
    ProviderRegistry.register("fake", _ReplacementSearcher)
    cfg = DatabaseConfig(name="fake")
    searcher = ProviderRegistry.get("fake", cfg, "x@y.com")
    assert isinstance(searcher, _ReplacementSearcher)


def test_get_forwards_config_and_email():
    received = {}

    class _CapturingSearcher(_FakeSearcher):
        def __init__(self, config: DatabaseConfig, email: str) -> None:
            super().__init__(config, email)
            received["config"] = config
            received["email"] = email

    ProviderRegistry.register("capturing", _CapturingSearcher)
    cfg = DatabaseConfig(name="cap", rate_limit=0.5)
    ProviderRegistry.get("capturing", cfg, "hello@world.com")
    assert received["email"] == "hello@world.com"
    assert received["config"].rate_limit == 0.5
