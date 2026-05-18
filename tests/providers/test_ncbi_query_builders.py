import pytest
from biocurator.providers.base import NCBIDatabase
from biocurator.providers.ncbi_criteria import NCBISearchCriteria
from biocurator.providers.ncbi_query_builders import (
    GeneQueryBuilder,
    LiteratureQueryBuilder,
    SRAQueryBuilder,
    SequenceQueryBuilder,
    TaxonomyQueryBuilder,
    get_builder,
)

# --- SequenceQueryBuilder ---
def test_sequence_builder_organism():
    b = SequenceQueryBuilder()
    q = b.build(NCBISearchCriteria(organism="Homo sapiens"))
    assert '"Homo sapiens"[Organism]' in q

def test_sequence_builder_keywords():
    b = SequenceQueryBuilder()
    q = b.build(NCBISearchCriteria(keywords=["kinase", "cancer"]))
    assert '"kinase"' in q and '"cancer"' in q

def test_sequence_builder_length_range():
    b = SequenceQueryBuilder()
    q = b.build(NCBISearchCriteria(min_length=100, max_length=500))
    assert "100:500[Sequence Length]" in q

def test_sequence_builder_min_length_only():
    b = SequenceQueryBuilder()
    q = b.build(NCBISearchCriteria(min_length=200))
    assert "200:999999999[Sequence Length]" in q

def test_sequence_builder_max_length_only():
    b = SequenceQueryBuilder()
    q = b.build(NCBISearchCriteria(max_length=800))
    assert "1:800[Sequence Length]" in q

def test_sequence_builder_date_range():
    b = SequenceQueryBuilder()
    q = b.build(NCBISearchCriteria(start_date="2020/01/01", end_date="2024/12/31"))
    assert '"2020/01/01"[Publication Date]' in q
    assert '"2024/12/31"[Publication Date]' in q

def test_sequence_builder_taxonomy_filter():
    b = SequenceQueryBuilder()
    q = b.build(NCBISearchCriteria(taxonomy_filter="Mammalia"))
    assert '"Mammalia"[Organism]' in q

def test_sequence_builder_location():
    b = SequenceQueryBuilder()
    q = b.build(NCBISearchCriteria(location="Africa, Asia"))
    assert '"Africa"' in q and '"Asia"' in q

def test_sequence_builder_exclude_terms():
    b = SequenceQueryBuilder()
    q = b.build(NCBISearchCriteria(exclude_terms=["predicted", "synthetic"]))
    assert 'NOT "predicted"' in q
    assert 'NOT "synthetic"' in q

def test_sequence_builder_empty_criteria():
    b = SequenceQueryBuilder()
    assert b.build(NCBISearchCriteria()) == ""

def test_sequence_builder_available_fields_returns_dict():
    b = SequenceQueryBuilder()
    fields = b.available_fields()
    assert isinstance(fields, dict)
    assert "ORGN" in fields
    assert "SLEN" in fields
    assert "PDAT" in fields

# --- LiteratureQueryBuilder ---
def test_literature_builder_organism():
    b = LiteratureQueryBuilder()
    q = b.build(NCBISearchCriteria(organism="Homo sapiens"))
    assert '"Homo sapiens"[MeSH Terms]' in q

def test_literature_builder_keywords():
    b = LiteratureQueryBuilder()
    q = b.build(NCBISearchCriteria(keywords=["kinase", "cancer"]))
    assert '"kinase"[Title/Abstract]' in q
    assert '"cancer"[Title/Abstract]' in q

def test_literature_builder_date_range():
    b = LiteratureQueryBuilder()
    q = b.build(NCBISearchCriteria(start_date="2020/01/01", end_date="2024/12/31"))
    assert '"2020/01/01"[Date - Publication]' in q

def test_literature_builder_ignores_length():
    b = LiteratureQueryBuilder()
    q = b.build(NCBISearchCriteria(min_length=100, max_length=500))
    assert "[Sequence Length]" not in q

def test_literature_builder_available_fields():
    b = LiteratureQueryBuilder()
    fields = b.available_fields()
    assert "MESH" in fields
    assert "TIAB" in fields
    assert "JOUR" in fields

# --- GeneQueryBuilder ---
def test_gene_builder_organism():
    b = GeneQueryBuilder()
    q = b.build(NCBISearchCriteria(organism="Mus musculus"))
    assert '"Mus musculus"[Organism]' in q

def test_gene_builder_keywords():
    b = GeneQueryBuilder()
    q = b.build(NCBISearchCriteria(keywords=["BRCA1"]))
    assert '"BRCA1"[Gene/Protein Name]' in q

def test_gene_builder_date_range_uses_mdat():
    b = GeneQueryBuilder()
    q = b.build(NCBISearchCriteria(start_date="2020/01/01", end_date="2024/12/31"))
    assert "[Modification Date]" in q

def test_gene_builder_available_fields():
    b = GeneQueryBuilder()
    fields = b.available_fields()
    assert "CHR" in fields
    assert "DIS" in fields
    assert "GO" in fields

# --- SRAQueryBuilder ---
def test_sra_builder_organism():
    b = SRAQueryBuilder()
    q = b.build(NCBISearchCriteria(organism="Homo sapiens"))
    assert '"Homo sapiens"[Organism]' in q

def test_sra_builder_ignores_length():
    b = SRAQueryBuilder()
    q = b.build(NCBISearchCriteria(min_length=100))
    assert "[Sequence Length]" not in q

def test_sra_builder_available_fields():
    b = SRAQueryBuilder()
    fields = b.available_fields()
    assert "PLAT" in fields
    assert "STRA" in fields
    assert "MBS" in fields

# --- TaxonomyQueryBuilder ---
def test_taxonomy_builder_organism_uses_scin():
    b = TaxonomyQueryBuilder()
    q = b.build(NCBISearchCriteria(organism="Homo sapiens"))
    assert '"Homo sapiens"[Scientific Name]' in q

def test_taxonomy_builder_ignores_length_and_dates():
    b = TaxonomyQueryBuilder()
    q = b.build(NCBISearchCriteria(min_length=100, start_date="2020/01/01"))
    assert "[Sequence Length]" not in q
    assert "[Publication Date]" not in q

def test_taxonomy_builder_available_fields():
    b = TaxonomyQueryBuilder()
    fields = b.available_fields()
    assert "SCIN" in fields
    assert "RANK" in fields
    assert "LNGE" in fields

# --- factory ---
def test_get_builder_nuccore():
    assert isinstance(get_builder(NCBIDatabase.NUCCORE), SequenceQueryBuilder)

def test_get_builder_protein():
    assert isinstance(get_builder(NCBIDatabase.PROTEIN), SequenceQueryBuilder)

def test_get_builder_pubmed():
    assert isinstance(get_builder(NCBIDatabase.PUBMED), LiteratureQueryBuilder)

def test_get_builder_gene():
    assert isinstance(get_builder(NCBIDatabase.GENE), GeneQueryBuilder)

def test_get_builder_sra():
    assert isinstance(get_builder(NCBIDatabase.SRA), SRAQueryBuilder)

def test_get_builder_taxonomy():
    assert isinstance(get_builder(NCBIDatabase.TAXONOMY), TaxonomyQueryBuilder)

def test_get_builder_unknown_raises():
    with pytest.raises(ValueError):
        get_builder("not_a_db")  # type: ignore
