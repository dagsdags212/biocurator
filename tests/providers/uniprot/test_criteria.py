from biocurator.providers.base import SearchCriteria
from biocurator.providers.uniprot import UniProtSearchCriteria


def test_uniprot_criteria_is_search_criteria_subclass():
    assert issubclass(UniProtSearchCriteria, SearchCriteria)


def test_uniprot_criteria_reviewed_default_is_none():
    c = UniProtSearchCriteria()
    assert c.reviewed is None


def test_uniprot_criteria_reviewed_true():
    c = UniProtSearchCriteria(reviewed=True)
    assert c.reviewed is True


def test_uniprot_criteria_reviewed_false():
    c = UniProtSearchCriteria(reviewed=False)
    assert c.reviewed is False


def test_uniprot_criteria_inherits_base_fields():
    c = UniProtSearchCriteria(organism="Homo sapiens", keywords=["kinase"])
    assert c.organism == "Homo sapiens"
    assert "kinase" in c.keywords
