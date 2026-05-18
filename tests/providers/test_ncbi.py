import pytest
from biocurator.providers.base import DatabaseConfig
from biocurator.providers.ncbi import NCBISearcher
from biocurator.providers.ncbi_criteria import NCBISearchCriteria
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
    query = searcher.build_query(criteria)
    assert '"Mus musculus"[Organism]' in query
