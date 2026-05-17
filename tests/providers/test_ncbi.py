import pytest
from biocurator.providers.base import SearchCriteria, DatabaseConfig
from biocurator.providers.ncbi import NCBISearcher
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
    criteria = SearchCriteria(organism="Homo sapiens")
    query = searcher.build_query(criteria)
    assert '"Homo sapiens"[Organism]' in query


def test_build_query_keywords(searcher):
    criteria = SearchCriteria(keywords=["kinase", "cancer"])
    query = searcher.build_query(criteria)
    assert '"kinase"' in query
    assert '"cancer"' in query


def test_build_query_length_range(searcher):
    criteria = SearchCriteria(min_length=100, max_length=500)
    query = searcher.build_query(criteria)
    assert "100:500[Sequence Length]" in query


def test_build_query_exclude_terms(searcher):
    criteria = SearchCriteria(exclude_terms=["predicted", "synthetic"])
    query = searcher.build_query(criteria)
    assert 'NOT "predicted"' in query
    assert 'NOT "synthetic"' in query


def test_build_query_empty_criteria(searcher):
    query = searcher.build_query(SearchCriteria())
    assert query == ""
