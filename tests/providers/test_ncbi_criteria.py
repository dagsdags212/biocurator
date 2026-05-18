from biocurator.providers.ncbi_criteria import NCBISearchCriteria
from biocurator.providers.base import NCBIDatabase, SearchCriteria


def test_ncbi_criteria_is_search_criteria_subclass():
    assert issubclass(NCBISearchCriteria, SearchCriteria)

def test_ncbi_criteria_default_database():
    c = NCBISearchCriteria()
    assert c.database == NCBIDatabase.NUCCORE

def test_ncbi_criteria_accepts_database():
    c = NCBISearchCriteria(database=NCBIDatabase.PUBMED)
    assert c.database == NCBIDatabase.PUBMED

def test_ncbi_criteria_has_taxonomy_filter():
    c = NCBISearchCriteria(taxonomy_filter="Mammalia")
    assert c.taxonomy_filter == "Mammalia"

def test_ncbi_criteria_has_location():
    c = NCBISearchCriteria(location="Africa, Asia")
    assert c.location == "Africa, Asia"

def test_ncbi_criteria_inherits_base_fields():
    c = NCBISearchCriteria(organism="Homo sapiens", keywords=["kinase"])
    assert c.organism == "Homo sapiens"
    assert "kinase" in c.keywords
