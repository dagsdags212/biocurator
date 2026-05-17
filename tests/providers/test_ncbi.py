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


def test_build_query_min_length_only(searcher):
    criteria = SearchCriteria(min_length=200)
    query = searcher.build_query(criteria)
    assert "200:999999999[Sequence Length]" in query


def test_build_query_max_length_only(searcher):
    criteria = SearchCriteria(max_length=800)
    query = searcher.build_query(criteria)
    assert "1:800[Sequence Length]" in query


def test_build_query_date_range(searcher):
    criteria = SearchCriteria(start_date="2020/01/01", end_date="2024/12/31")
    query = searcher.build_query(criteria)
    assert '"2020/01/01"[Publication Date]' in query
    assert '"2024/12/31"[Publication Date]' in query


def test_build_query_taxonomy_filter(searcher):
    criteria = SearchCriteria(taxonomy_filter="Mammalia")
    query = searcher.build_query(criteria)
    assert '"Mammalia"[Organism]' in query


def test_build_query_location(searcher):
    criteria = SearchCriteria(location="Africa, Asia")
    query = searcher.build_query(criteria)
    assert '"Africa"' in query
    assert '"Asia"' in query


def test_build_query_multiple_parts_joined_with_and(searcher):
    criteria = SearchCriteria(organism="Mus musculus", keywords=["receptor"])
    query = searcher.build_query(criteria)
    assert " AND " in query
    assert '"Mus musculus"[Organism]' in query
    assert '"receptor"' in query
