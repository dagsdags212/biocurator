"""
Tests for SequenceFilter methods.
"""

import pytest
from biocurator.core.filters import SequenceFilter
from biocurator.providers.base import SequenceRecord


def make_seq(accession: str, organism: str = "", title: str = "", sequence: str | None = None) -> SequenceRecord:
    return SequenceRecord(
        id=accession,
        accession=accession,
        title=title,
        organism=organism,
        sequence=sequence,
        database="NCBI",
    )


# --- filter_by_taxonomy ---

def test_filter_by_taxonomy_matches_organism():
    seqs = [
        make_seq("A", organism="Homo sapiens"),
        make_seq("B", organism="Mus musculus"),
        make_seq("C", organism="Homo sapiens neanderthalensis"),
    ]
    result = SequenceFilter.filter_by_taxonomy(seqs, "Homo")
    assert len(result) == 2
    assert result[0].accession == "A"
    assert result[1].accession == "C"


def test_filter_by_taxonomy_matches_title():
    seqs = [
        make_seq("A", title="Homo sapiens genome", organism=""),
        make_seq("B", title="Mouse genome", organism=""),
    ]
    result = SequenceFilter.filter_by_taxonomy(seqs, "Homo")
    assert len(result) == 1
    assert result[0].accession == "A"


def test_filter_by_taxonomy_case_insensitive():
    seqs = [make_seq("A", organism="HOMO SAPIENS")]
    result = SequenceFilter.filter_by_taxonomy(seqs, "homo")
    assert len(result) == 1


def test_filter_by_taxonomy_no_match():
    seqs = [make_seq("A", organism="E. coli")]
    result = SequenceFilter.filter_by_taxonomy(seqs, "Homo")
    assert len(result) == 0


# --- remove_duplicates ---

def test_remove_duplicates_by_sequence():
    seqs = [
        make_seq("A", sequence="ATGC"),
        make_seq("B", sequence="ATGC"),  # duplicate sequence
        make_seq("C", sequence="GGCC"),
    ]
    result = SequenceFilter.remove_duplicates(seqs, by="sequence")
    assert len(result) == 2
    assert [s.accession for s in result] == ["A", "C"]


def test_remove_duplicates_by_accession():
    seqs = [
        make_seq("ABC123"),
        make_seq("ABC123"),  # duplicate accession
        make_seq("XYZ789"),
    ]
    result = SequenceFilter.remove_duplicates(seqs, by="accession")
    assert len(result) == 2
    assert [s.accession for s in result] == ["ABC123", "XYZ789"]


def test_remove_duplicates_no_duplicates():
    seqs = [make_seq("A", sequence="ATGC"), make_seq("B", sequence="GGCC")]
    result = SequenceFilter.remove_duplicates(seqs, by="sequence")
    assert len(result) == 2


def test_remove_duplicates_all_duplicates():
    seqs = [make_seq("A", sequence="ATGC"), make_seq("B", sequence="ATGC")]
    result = SequenceFilter.remove_duplicates(seqs, by="sequence")
    assert len(result) == 1


# --- filter_by_date_range ---

def test_filter_by_date_range_start_date():
    seqs = [
        make_seq("A"),
        make_seq("B"),
        make_seq("C"),
    ]
    seqs[0].create_date = "2023/01/01"
    seqs[1].create_date = "2024/06/15"
    seqs[2].create_date = "2025/12/31"

    result = SequenceFilter.filter_by_date_range(seqs, start_date="2024/01/01")
    assert len(result) == 2
    assert result[0].accession == "B"
    assert result[1].accession == "C"


def test_filter_by_date_range_end_date():
    seqs = [
        make_seq("A"),
        make_seq("B"),
        make_seq("C"),
    ]
    seqs[0].create_date = "2023/01/01"
    seqs[1].create_date = "2024/06/15"
    seqs[2].create_date = "2025/12/31"

    result = SequenceFilter.filter_by_date_range(seqs, end_date="2024/06/15")
    assert len(result) == 2
    assert result[0].accession == "A"
    assert result[1].accession == "B"


def test_filter_by_date_range_both_dates():
    seqs = [
        make_seq("A"),
        make_seq("B"),
        make_seq("C"),
    ]
    seqs[0].create_date = "2023/01/01"
    seqs[1].create_date = "2024/06/15"
    seqs[2].create_date = "2025/12/31"

    result = SequenceFilter.filter_by_date_range(seqs, start_date="2023/06/01", end_date="2025/01/01")
    assert len(result) == 1
    assert result[0].accession == "B"


def test_filter_by_date_range_no_dates():
    seqs = [make_seq("A"), make_seq("B")]
    result = SequenceFilter.filter_by_date_range(seqs)
    assert len(result) == 2


def test_filter_by_date_range_includes_unparseable():
    """Sequences with unparseable create dates are included (not rejected)."""
    seqs = [make_seq("A"), make_seq("B")]
    seqs[0].create_date = "2024/01/01"
    seqs[1].create_date = "not-a-date"

    result = SequenceFilter.filter_by_date_range(seqs, start_date="2024/01/01")
    assert len(result) == 2  # both included: one matches, one has unparseable date


def test_filter_by_date_range_missing_dates_included():
    """Sequences with empty create_date are included when filtering."""
    seqs = [make_seq("A"), make_seq("B")]
    seqs[0].create_date = "2024/01/01"
    seqs[1].create_date = ""  # missing date

    result = SequenceFilter.filter_by_date_range(seqs, start_date="2024/01/01")
    assert len(result) == 2


def test_filter_by_date_range_invalid_start_date_logs_warning(caplog):
    """Invalid start_date format logs a warning and returns all sequences."""
    seqs = [make_seq("A")]
    seqs[0].create_date = "2024/01/01"

    import logging
    with caplog.at_level(logging.WARNING):
        result = SequenceFilter.filter_by_date_range(seqs, start_date="bad-date")

    assert len(result) == 1
    assert "Invalid start date format" in caplog.text
