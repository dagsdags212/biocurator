import pytest
from biocurator.providers.base import DatabaseConfig
from biocurator.providers.uniprot import UniProtSearcher, UniProtSearchCriteria
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
    criteria = UniProtSearchCriteria(organism="Mus musculus")
    query = searcher.build_query(criteria)
    assert 'organism:"Mus musculus"' in query


def test_build_query_keywords(searcher):
    criteria = UniProtSearchCriteria(keywords=["kinase", "receptor"])
    query = searcher.build_query(criteria)
    assert "(kinase OR receptor)" in query


def test_build_query_length_min(searcher):
    criteria = UniProtSearchCriteria(min_length=50)
    query = searcher.build_query(criteria)
    assert "length:[50 TO *]" in query


def test_build_query_length_max(searcher):
    criteria = UniProtSearchCriteria(max_length=300)
    query = searcher.build_query(criteria)
    assert "length:[* TO 300]" in query


def test_build_query_empty_criteria(searcher):
    query = searcher.build_query(UniProtSearchCriteria())
    assert query == ""


def test_build_query_multiple_parts_joined_with_and(searcher):
    criteria = UniProtSearchCriteria(organism="Homo sapiens", keywords=["kinase"])
    query = searcher.build_query(criteria)
    assert " AND " in query
    assert 'organism:"Homo sapiens"' in query
    assert "(kinase)" in query


def test_search_raises_database_search_error_on_failure(searcher):
    from biocurator.exceptions import DatabaseSearchError

    criteria = UniProtSearchCriteria(organism="Homo sapiens")
    with pytest.MonkeyPatch.context() as mp:

        def _fail(*args, **kwargs):
            raise ConnectionError("connection refused")

        mp.setattr(searcher, "_safe_get", _fail)
        with pytest.raises(DatabaseSearchError, match="UniProt search error"):
            searcher.search(criteria)


def test_search_raises_database_search_error_on_http_400(searcher):
    """4xx errors should NOT be retried, but should still raise DatabaseSearchError."""
    import requests
    from biocurator.exceptions import DatabaseSearchError

    criteria = UniProtSearchCriteria(organism="Homo sapiens")
    response = requests.Response()
    response.status_code = 400
    http_error = requests.HTTPError(response=response)
    with pytest.MonkeyPatch.context() as mp:

        def _fail(*args, **kwargs):
            raise http_error

        mp.setattr(searcher, "_safe_get", _fail)
        with pytest.raises(DatabaseSearchError, match="UniProt search error"):
            searcher.search(criteria)


def test_fetch_metadata_continues_on_batch_failure(searcher):
    criteria = UniProtSearchCriteria(organism="Homo sapiens")
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            searcher,
            "_safe_get",
            lambda *a, **kw: (_ for _ in ()).throw(Exception("batch failed")),
        )
        results = list(searcher.fetch_metadata(["P12345", "P67890"], criteria))
        assert results == []


def test_download_continues_on_single_failure(searcher):
    import tempfile
    from pathlib import Path

    criteria = UniProtSearchCriteria(organism="Homo sapiens")
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            searcher,
            "_safe_get",
            lambda *a, **kw: (_ for _ in ()).throw(Exception("download failed")),
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            results = list(searcher.download(["P12345"], Path(tmpdir), criteria))
            assert results == []
