"""
Sequence Filtering Module
=========================

This module provides filtering capabilities for biological sequences
based on various criteria such as length, quality, organism, location, etc.


© Jan Emmanuel Samson (2026-)
"""

from typing import List, Dict, Any, Optional
from biocurator.utils.logging import get_logger

logger = get_logger(__name__)


class SequenceFilter:
    """Helper class for filtering sequence sets based on custom criteria"""

    @staticmethod
    def filter_by_criteria(
        sequences: List[Dict[str, Any]], criteria
    ) -> List[Dict[str, Any]]:
        """Apply filtering criteria to a sequence set

        Parameters
        ----------
        sequences : List[Dict[str, Any]]
            List of sequence dictionaries to filter
        criteria : SearchCriteria
            Search criteria containing filter parameters

        Returns
        -------
        List[Dict[str, Any]]
            Filtered list of sequences
        """
        logger.info("Applying additional filters...")

        filtered = sequences.copy()
        initial_count = len(filtered)

        # Length filter
        if criteria.min_length:
            filtered = [
                s
                for s in filtered
                if s.get("sequence_length", 0) >= criteria.min_length
            ]
            logger.info(
                f"Length filter (min {criteria.min_length}): {len(filtered)} sequences remain"
            )

        if criteria.max_length:
            filtered = [
                s
                for s in filtered
                if s.get("sequence_length", 0) <= criteria.max_length
            ]
            logger.info(
                f"Length filter (max {criteria.max_length}): {len(filtered)} sequences remain"
            )

        # Organism filter — only runs when records carry a populated organism field.
        # NCBI esummary doesn't include an Organism field, so records fetched at the
        # metadata stage will have organism="" and would be incorrectly rejected.
        if criteria.organism and filtered and filtered[0].get("organism"):
            organism_lower = criteria.organism.lower()
            filtered = [
                s for s in filtered if organism_lower in s.get("organism", "").lower()
            ]
            logger.info(f"Organism filter: {len(filtered)} sequences remain")

        # Location filter (search in title and description)
        if criteria.location and filtered:
            location_terms = [
                term.strip().lower() for term in criteria.location.split(",")
            ]
            new_filtered = []
            for seq in filtered:
                title_desc = (
                    f"{seq.get('title', '')} {seq.get('description', '')}".lower()
                )
                if any(term in title_desc for term in location_terms):
                    new_filtered.append(seq)
            filtered = new_filtered
            logger.info(f"Location filter: {len(filtered)} sequences remain")

        # Exclude terms
        if criteria.exclude_terms and filtered:
            for exclude_term in criteria.exclude_terms:
                exclude_lower = exclude_term.lower()
                filtered = [
                    s
                    for s in filtered
                    if exclude_lower
                    not in f"{s.get('title', '')} {s.get('description', '')}".lower()
                ]
            logger.info(f"Exclude terms filter: {len(filtered)} sequences remain")

        # Quality filter — deferred to after download; sequences without actual
        # sequence data (metadata-only records) would score 0.0 and be incorrectly
        # rejected.  Use SequenceFilter.apply_quality_filter() on downloaded sequences.
        if criteria.quality_threshold and filtered:
            if any(s.get("sequence") for s in filtered):
                filtered = SequenceFilter.__filter_by_quality(
                    filtered, criteria.quality_threshold
                )
                logger.info(f"Quality filter: {len(filtered)} sequences remain")
            else:
                logger.info(
                    "Quality filter deferred: sequence data not yet available"
                )

        logger.info(
            f"Filtering complete: {len(filtered)}/{initial_count} sequences passed filters"
        )
        return filtered

    @staticmethod
    def apply_quality_filter(
        sequences: List[Dict[str, Any]], threshold: float
    ) -> List[Dict[str, Any]]:
        """Apply quality filtering to downloaded sequences.

        Parameters
        ----------
        sequences : List[Dict[str, Any]]
            Sequences that include actual sequence data.
        threshold : float
            Minimum quality score (0.0–1.0).

        Returns
        -------
        List[Dict[str, Any]]
            Sequences whose quality score meets the threshold.
        """
        return SequenceFilter.__filter_by_quality(sequences, threshold)

    @staticmethod
    def __filter_by_quality(
        sequences: List[Dict[str, Any]], threshold: float
    ) -> List[Dict[str, Any]]:
        """Filter sequences by quality score.

        Parameters
        ----------
        sequences : List[Dict[str, Any]]
            List of sequence dictionaries
        threshold : float
            Minimum quality threshold

        Returns
        -------
        List[Dict[str, Any]]
            Sequences passing quality filter
        """
        filtered = []
        for seq in sequences:
            quality_score = SequenceFilter.__calculate_quality_score(seq)
            if quality_score >= threshold:
                seq["quality_score"] = quality_score
                filtered.append(seq)

        return filtered

    @staticmethod
    def __calculate_quality_score(sequence: Dict[str, Any]) -> float:
        """Calculate a simple quality score for a sequence.

        Parameters
        ----------
        sequence : Dict[str, Any]
            Sequence dictionary

        Returns
        -------
        float
            Quality score between 0 and 1
        """
        score = 1.0

        # Check for sequence
        if not sequence.get("sequence"):
            return 0.0

        seq_str = sequence["sequence"].upper()

        # Penalize for high N content (nucleotide sequences)
        if any(base in seq_str for base in "ATGC"):
            n_content = seq_str.count("N") / len(seq_str)
            score -= n_content * 0.5

        # Penalize for high X content (protein sequences)
        if any(aa in seq_str for aa in "ACDEFGHIKLMNPQRSTVWY"):
            x_content = seq_str.count("X") / len(seq_str)
            score -= x_content * 0.5

        # Bonus for having metadata
        if sequence.get("organism"):
            score += 0.1

        if sequence.get("title") and len(sequence["title"]) > 10:
            score += 0.1

        # Ensure score is between 0 and 1
        return max(0.0, min(1.0, score))

    @staticmethod
    def remove_duplicates(
        sequences: List[Dict[str, Any]], by: str = "sequence"
    ) -> List[Dict[str, Any]]:
        """Remove duplicate sequences.

        Parameters
        ----------
        sequences : List[Dict[str, Any]]
            List of sequence dictionaries
        by : str
            Field to use for duplicate detection ('sequence', 'accession', etc.)

        Returns
        -------
        List[Dict[str, Any]]
            Deduplicated sequences
        """
        seen = set()
        deduplicated = []

        for seq in sequences:
            key = seq.get(by)
            if key and key not in seen:
                seen.add(key)
                deduplicated.append(seq)

        logger.info(f"Removed {len(sequences) - len(deduplicated)} duplicate sequences")
        return deduplicated

    @staticmethod
    def filter_by_taxonomy(
        sequences: List[Dict[str, Any]], taxonomy_filter: str
    ) -> List[Dict[str, Any]]:
        """Filter sequences by taxonomic classification.

        Parameters
        ----------
        sequences : List[Dict[str, Any]]
            List of sequence dictionaries
        taxonomy_filter : str
            Taxonomic filter term

        Returns
        -------
        List[Dict[str, Any]]
            Filtered sequences
        """
        taxonomy_lower = taxonomy_filter.lower()
        filtered = []

        for seq in sequences:
            organism = seq.get("organism", "").lower()
            title = seq.get("title", "").lower()

            if taxonomy_lower in organism or taxonomy_lower in title:
                filtered.append(seq)

        logger.info(
            f"Taxonomy filter '{taxonomy_filter}': {len(filtered)} sequences remain"
        )
        return filtered

    @staticmethod
    def filter_by_date_range(
        sequences: List[Dict[str, Any]],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Filter sequences by date range.

        Parameters
        ----------
        sequences : List[Dict[str, Any]]
            List of sequence dictionaries
        start_date : str, optional
            Start date in YYYY/MM/DD format
        end_date : str, optional
            End date in YYYY/MM/DD format

        Returns
        -------
        List[Dict[str, Any]]
            Filtered sequences
        """
        from datetime import datetime

        filtered = sequences.copy()

        if start_date:
            try:
                start_dt = datetime.strptime(start_date, "%Y/%m/%d")
                new_filtered = []

                for seq in filtered:
                    create_date = seq.get("create_date", "")
                    if create_date:
                        try:
                            seq_dt = datetime.strptime(create_date, "%Y/%m/%d")
                            if seq_dt >= start_dt:
                                new_filtered.append(seq)
                        except ValueError:
                            # Include sequences with unparseable dates
                            new_filtered.append(seq)
                    else:
                        new_filtered.append(seq)

                filtered = new_filtered
                logger.info(f"Start date filter: {len(filtered)} sequences remain")

            except ValueError:
                logger.warning(f"Invalid start date format: {start_date}")

        if end_date:
            try:
                end_dt = datetime.strptime(end_date, "%Y/%m/%d")
                new_filtered = []

                for seq in filtered:
                    create_date = seq.get("create_date", "")
                    if create_date:
                        try:
                            seq_dt = datetime.strptime(create_date, "%Y/%m/%d")
                            if seq_dt <= end_dt:
                                new_filtered.append(seq)
                        except ValueError:
                            # Include sequences with unparseable dates
                            new_filtered.append(seq)
                    else:
                        new_filtered.append(seq)

                filtered = new_filtered
                logger.info(f"End date filter: {len(filtered)} sequences remain")

            except ValueError:
                logger.warning(f"Invalid end date format: {end_date}")

        return filtered
