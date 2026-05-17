import pytest
from biocurator.providers.base import SearchCriteria, DatabaseConfig
from biocurator.providers.uniprot import UniProtSearcher
from biocurator.providers.registry import ProviderRegistry


@pytest.fixture
def config():
    return DatabaseConfig(name="UniProt", rate_limit=0.0, batch_size=25)


@pytest.fixture
def searcher(config):
    return UniProtSearcher(config, "test@example.com")


def test_uniprot_registered():
    assert "uniprot" in ProviderRegistry.available()


def test_build_query_organism(searcher):
    criteria = SearchCriteria(organism="Mus musculus")
    query = searcher.build_query(criteria)
    assert 'organism:"Mus musculus"' in query


def test_build_query_keywords(searcher):
    criteria = SearchCriteria(keywords=["kinase", "receptor"])
    query = searcher.build_query(criteria)
    assert "(kinase OR receptor)" in query


def test_build_query_length_min(searcher):
    criteria = SearchCriteria(min_length=50)
    query = searcher.build_query(criteria)
    assert "length:[50 TO *]" in query


def test_build_query_length_max(searcher):
    criteria = SearchCriteria(max_length=300)
    query = searcher.build_query(criteria)
    assert "length:[* TO 300]" in query


def test_build_query_empty_criteria(searcher):
    query = searcher.build_query(SearchCriteria())
    assert query == ""


def test_build_query_length_min_and_max(searcher):
    criteria = SearchCriteria(min_length=100, max_length=500)
    query = searcher.build_query(criteria)
    assert "length:[100 TO *]" in query
    assert "length:[* TO 500]" in query


def test_build_query_multiple_parts_joined_with_and(searcher):
    criteria = SearchCriteria(organism="Homo sapiens", keywords=["kinase"])
    query = searcher.build_query(criteria)
    assert " AND " in query
    assert 'organism:"Homo sapiens"' in query
    assert "(kinase)" in query


def test_build_query_single_keyword(searcher):
    criteria = SearchCriteria(keywords=["phosphatase"])
    query = searcher.build_query(criteria)
    assert "(phosphatase)" in query
