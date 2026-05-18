from biocurator.providers.base import SequenceRecord


def test_required_fields():
    r = SequenceRecord(id="123", accession="NM_001.1", database="NCBI")
    assert r.id == "123"
    assert r.accession == "NM_001.1"
    assert r.database == "NCBI"


def test_optional_fields_default():
    r = SequenceRecord(id="123", accession="NM_001.1", database="NCBI")
    assert r.sequence is None
    assert r.organism == ""
    assert r.sequence_length == 0
    assert r.downloaded is False


def test_with_sequence():
    r = SequenceRecord(id="123", accession="NM_001.1", database="NCBI", sequence="ATGC", sequence_length=4)
    assert r.sequence == "ATGC"
    assert r.sequence_length == 4
