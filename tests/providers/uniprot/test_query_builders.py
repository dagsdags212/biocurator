from biocurator.providers.uniprot import UniProtQueryBuilder, UniProtSearchCriteria


def test_builder_organism():
    b = UniProtQueryBuilder()
    q = b.build(UniProtSearchCriteria(organism="Mus musculus"))
    assert 'organism:"Mus musculus"' in q


def test_builder_keywords():
    b = UniProtQueryBuilder()
    q = b.build(UniProtSearchCriteria(keywords=["kinase", "receptor"]))
    assert "(kinase OR receptor)" in q


def test_builder_single_keyword():
    b = UniProtQueryBuilder()
    q = b.build(UniProtSearchCriteria(keywords=["phosphatase"]))
    assert "(phosphatase)" in q


def test_builder_length_min():
    b = UniProtQueryBuilder()
    q = b.build(UniProtSearchCriteria(min_length=50))
    assert "length:[50 TO *]" in q


def test_builder_length_max():
    b = UniProtQueryBuilder()
    q = b.build(UniProtSearchCriteria(max_length=300))
    assert "length:[* TO 300]" in q


def test_builder_length_min_and_max():
    b = UniProtQueryBuilder()
    q = b.build(UniProtSearchCriteria(min_length=100, max_length=500))
    assert "length:[100 TO *]" in q
    assert "length:[* TO 500]" in q


def test_builder_reviewed_true():
    b = UniProtQueryBuilder()
    q = b.build(UniProtSearchCriteria(reviewed=True))
    assert "reviewed:true" in q


def test_builder_reviewed_false():
    b = UniProtQueryBuilder()
    q = b.build(UniProtSearchCriteria(reviewed=False))
    assert "reviewed:false" in q


def test_builder_empty_criteria():
    b = UniProtQueryBuilder()
    assert b.build(UniProtSearchCriteria()) == ""


def test_builder_multiple_parts_joined_with_and():
    b = UniProtQueryBuilder()
    q = b.build(UniProtSearchCriteria(organism="Homo sapiens", keywords=["kinase"]))
    assert " AND " in q
    assert 'organism:"Homo sapiens"' in q
    assert "(kinase)" in q


def test_builder_available_fields_returns_dict():
    b = UniProtQueryBuilder()
    fields = b.available_fields()
    assert isinstance(fields, dict)
    assert "organism_name" in fields
    assert "length" in fields
