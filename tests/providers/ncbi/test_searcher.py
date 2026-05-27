from pathlib import Path

import pytest
from unittest.mock import patch, MagicMock
from biocurator.providers.base import DatabaseConfig
from biocurator.providers.ncbi import NCBISearcher, NCBISearchCriteria
from biocurator.providers.registry import ProviderRegistry


@pytest.fixture
def config():
    return DatabaseConfig(name="NCBI", rate_limit=0.0, batch_size=20)


@pytest.fixture
def searcher(config):
    return NCBISearcher(config, "test@example.com")


def test_ncbi_registered():
    assert "ncbi" in ProviderRegistry.available()


def test_build_query_organism(searcher):
    criteria = NCBISearchCriteria(organism="Homo sapiens")
    query = searcher.build_query(criteria)
    assert '"Homo sapiens"[Organism]' in query


def test_build_query_keywords(searcher):
    criteria = NCBISearchCriteria(keywords=["kinase", "cancer"])
    query = searcher.build_query(criteria)
    assert '"kinase"' in query
    assert '"cancer"' in query


def test_build_query_length_range(searcher):
    criteria = NCBISearchCriteria(min_length=100, max_length=500)
    query = searcher.build_query(criteria)
    assert "100:500[Sequence Length]" in query


def test_build_query_exclude_terms(searcher):
    criteria = NCBISearchCriteria(exclude_terms=["predicted", "synthetic"])
    query = searcher.build_query(criteria)
    assert 'NOT "predicted"' in query
    assert 'NOT "synthetic"' in query


def test_build_query_empty_criteria(searcher):
    query = searcher.build_query(NCBISearchCriteria())
    assert query == ""


def test_build_query_min_length_only(searcher):
    criteria = NCBISearchCriteria(min_length=200)
    query = searcher.build_query(criteria)
    assert "200:999999999[Sequence Length]" in query


def test_build_query_max_length_only(searcher):
    criteria = NCBISearchCriteria(max_length=800)
    query = searcher.build_query(criteria)
    assert "1:800[Sequence Length]" in query


def test_build_query_date_range(searcher):
    criteria = NCBISearchCriteria(start_date="2020/01/01", end_date="2024/12/31")
    query = searcher.build_query(criteria)
    assert '"2020/01/01"[Publication Date]' in query
    assert '"2024/12/31"[Publication Date]' in query


def test_build_query_multiple_parts_joined_with_and(searcher):
    criteria = NCBISearchCriteria(organism="Mus musculus", keywords=["receptor"])
    query = searcher.build_query(criteria)
    assert " AND " in query
    assert '"Mus musculus"[Organism]' in query
    assert '"receptor"' in query


def test_build_query_delegates_to_builder(searcher):
    criteria = NCBISearchCriteria(organism="Mus musculus")
    mock_builder = MagicMock()
    mock_builder.build.return_value = "mocked_query"
    with patch(
        "biocurator.providers.ncbi.searcher.get_builder", return_value=mock_builder
    ) as mock_get:
        result = searcher.build_query(criteria)
        mock_get.assert_called_once_with(criteria.database)
        mock_builder.build.assert_called_once_with(criteria)
        assert result == "mocked_query"


def test_search_raises_database_search_error_on_network_failure(searcher):
    from biocurator.exceptions import DatabaseSearchError

    criteria = NCBISearchCriteria(organism="Homo sapiens")
    with patch.object(
        searcher, "_safe_entrez_call", side_effect=ConnectionError("no route to host")
    ):
        with pytest.raises(DatabaseSearchError, match="NCBI search error"):
            searcher.search(criteria)


def test_search_raises_database_search_error_on_retry_exhaustion(searcher):
    from biocurator.exceptions import DatabaseSearchError

    criteria = NCBISearchCriteria(organism="Homo sapiens")
    with patch.object(
        searcher, "_safe_entrez_call", side_effect=ConnectionError("timeout")
    ):
        with pytest.raises(DatabaseSearchError):
            searcher.search(criteria)


def test_fetch_metadata_continues_on_batch_failure(searcher):
    criteria = NCBISearchCriteria(organism="Homo sapiens")
    with patch.object(
        searcher, "_safe_entrez_call", side_effect=Exception("batch failed")
    ):
        results = list(searcher.fetch_metadata(["123", "456"], criteria))
        assert results == []


def test_download_continues_on_single_failure(searcher):
    criteria = NCBISearchCriteria(organism="Homo sapiens")
    with patch.object(
        searcher, "_fetch_single", side_effect=Exception("download failed")
    ):
        results = list(searcher.download(["123"], Path("/tmp"), criteria))
        assert results == []


def test_search_via_breaker_on_network_failure(searcher):
    """Breaker wraps search() and trips on repeated network failures."""
    from biocurator.config.schema import BreakerConfig
    from biocurator.exceptions import DatabaseSearchError

    # Configure a breaker that trips after 1 failure
    searcher.config.breaker = BreakerConfig(fail_max=1, recovery_timeout=60)
    searcher._breaker = searcher._init_breaker()
    assert searcher.breaker_state == "closed"

    criteria = NCBISearchCriteria(organism="Homo sapiens")
    with patch.object(
        searcher, "_safe_entrez_call", side_effect=ConnectionError("timeout")
    ):
        with pytest.raises(DatabaseSearchError):
            searcher.search(criteria)

    # Breaker should have tripped to open
    assert searcher.breaker_state == "open"


def test_search_breaker_closed_on_success(searcher):
    """Breaker remains closed when search succeeds."""
    from biocurator.config.schema import BreakerConfig

    searcher.config.breaker = BreakerConfig(fail_max=1, recovery_timeout=60)
    searcher._breaker = searcher._init_breaker()

    criteria = NCBISearchCriteria(organism="Homo sapiens")
    with patch.object(
        searcher, "_safe_entrez_call", return_value={"IdList": ["123"], "WebEnv": None, "QueryKey": None}
    ):
        result = searcher.search(criteria)

    assert searcher.breaker_state == "closed"
    assert result == ["123"]
