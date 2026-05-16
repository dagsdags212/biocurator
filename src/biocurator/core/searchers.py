"""
Database Searchers API
======================

This module implements the logic for querying various biological databases
including NCBI and UniProt. Each searcher implements the DatabaseSearcher interface
for consistent API across different datasoruces.

© Jan Emmanuel Samson (2026-)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any
import time
from io import StringIO

try:
    from Bio import Entrez
    from Bio import SeqIO
    import requests
    from biocurator.utils.logging import get_logger
except ImportError as exc:
    raise ImportError(f"Required package not available: {exc}")


logger = get_logger(__name__)


@dataclass
class SearchCriteria:
    """Data model for search criteria"""

    organism: Optional[str] = None
    sequence_type: str = "nucleotide"
    keywords: List[str] = field(default_factory=list)
    location: Optional[str] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    max_results: int = 100
    exclude_terms: List[str] = field(default_factory=list)
    taxonomy_filter: Optional[str] = None
    quality_threshold: Optional[float] = None


@dataclass
class DatabaseConfig:
    """Data model for storing database access configuration"""

    name: str
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    rate_limit: float = 0.3
    batch_size: int = 20
    timeout: int = 30


class DatabaseSearcher(ABC):
    """Abstract base class for database searchers"""

    def __init__(self, config: DatabaseConfig, email: str) -> None:
        self.config = config
        self.email = email
        self.session = requests.Session()

    @abstractmethod
    def search(self, criteria: SearchCriteria) -> List[str]:
        """Query a database a return a list of IDs"""
        pass

    @abstractmethod
    def fetch_metadata(self, ids: List[str]) -> List[Dict[str, Any]]:
        """Retrieve metadata for a set of IDs"""
        pass

    @abstractmethod
    def download(self, ids: List[str], outdir: Path) -> List[Dict[str, Any]]:
        """Download sequences and return associated metadata"""
        pass


class NCBISearcher(DatabaseSearcher):
    """NCBI database searcher for nucleotide, protein, and SRA databases"""

    def __init__(self, config: DatabaseConfig, email: str) -> None:
        super().__init__(config, email)
        Entrez.email = email
        Entrez.tool = "Biocurator"

        self.db_mapping = {
            "nucleotide": "nucleotide",
            "protein": "protein",
            "sra": "sra",
        }

    def search(self, criteria: SearchCriteria) -> List[str]:
        """Query from an NCBI database"""
        logger.info(f"Searching NCBI {criteria.sequence_type} database...")

        query_parts = []

        if criteria.organism:
            query_parts.append(f'"{criteria.organism}"[Organism]')

        if criteria.keywords:
            kw_query = " OR ".join([f'"{kw}"' for kw in criteria.keywords])
            query_parts.append(kw_query)

        if criteria.location:
            loc_terms = criteria.location.split(",")
            loc_query = " OR ".join([f'"{loc.strip()}"' for loc in loc_terms])
            query_parts.append(loc_query)

        if criteria.min_length and criteria.max_length:
            query_parts.append(
                f"{criteria.min_length}:{criteria.max_length}[Sequence Length]"
            )
        elif criteria.min_length:
            query_parts.append(f"{criteria.min_length}:999999999[Sequence Length]")
        elif criteria.max_length:
            query_parts.append(f"1:{criteria.max_length}[Sequence Length]")

        if criteria.start_date and criteria.end_date:
            query_parts.append(
                f'"{criteria.start_date}"[Publication Date]:"{criteria.end_date}"[Publication Date]'
            )

        if criteria.taxonomy_filter:
            query_parts.append(f'"{criteria.taxonomy_filter}"[Organism]')

        if criteria.exclude_terms:
            for term in criteria.exclude_terms:
                query_parts.append(f'NOT "{term}"')

        query = " AND ".join(query_parts)
        logger.info(f"Search query: {query}")

        try:
            db = self.db_mapping.get(criteria.sequence_type, "nucleotide")
            handle = Entrez.esearch(
                db=db, term=query, retmax=criteria.max_results, sort="relevance"
            )
            results = Entrez.read(handle)
            handle.close()

            id_list = results["IdList"]
            logger.info(f"Found {len(id_list)} potential sequences")

            return id_list

        except Exception as exc:
            logger.error(f"Error searching NCBI: {exc}")
            return []

    def fetch_metadata(self, ids: List[str]) -> List[Dict[str, Any]]:
        """Retrieve metadata for a list of NCBI accessions"""
        logger.info(f"Fetching metadata for {len(ids)} sequences...")

        metadata_list = []
        batch_size = self.config.batch_size

        for i in range(0, len(ids), batch_size):
            batch = ids[i : i + batch_size]

            try:
                handle = Entrez.esummary(
                    db=self.db_mapping.get("nucleotide", "nucleotide"),
                    id=",".join(batch),
                )
                summaries = Entrez.read(handle)
                handle.close()

                for summary in summaries:
                    metadata_list.append(
                        {
                            "id": summary.get("Id", ""),
                            "accession": summary.get("AccessionVersion", ""),
                            "title": summary.get("Title", ""),
                            "organism": summary.get("Organism", ""),
                            "length": int(summary.get("Length", 0)),
                            "create_date": summary.get("CreateDate", ""),
                            "update_date": summary.get("UpdateDate", ""),
                            "authors": summary.get("AuthorList", ""),
                            "journal": summary.get("Source", ""),
                            "taxonomy_id": summary.get("TaxId", ""),
                            "database": "NCBI",
                        }
                    )
                    time.sleep(self.config.rate_limit)

            except Exception as exc:
                logger.warning(
                    f"Error fetching metadata for batch {i//batch_size+1}: {exc}"
                )

        logger.info(f"Retrieved metadata for {len(metadata_list)} sequences")
        return metadata_list

    def download(self, ids: List[str], outdir: Path) -> List[Dict[str, Any]]:
        """Download sequence data from a list of NCBI accessions"""
        logger.info(f"Attempting to download {len(ids)} sequences...")

        downloaded_sequences = []

        for seq_id in ids:
            try:
                handle = Entrez.efetch(
                    db=self.db_mapping.get("nucleotide", "nucleotide"),
                    id=seq_id,
                    rettype="fasta",
                    retmode="text",
                )

                record = SeqIO.read(handle, "fasta")
                handle.close()

                seq_info = {
                    "id": seq_id,
                    "accession": record.id,
                    "description": record.description,
                    "sequence_length": len(record.seq),
                    "sequence": str(record.seq),
                    "downloaded": True,
                }

                downloaded_sequences.append(seq_info)
                logger.debug(f"Downloaded {record.id} ({len(record.seq)} bp)")

                time.sleep(self.config.rate_limit)

            except Exception as e:
                logger.warning(f"Failed to download {seq_id}: {e}")
                continue

        logger.info(f"Successfully downloaded {len(downloaded_sequences)} sequences")
        return downloaded_sequences


class UniProtSearcher(DatabaseSearcher):
    """UniProt database searcher for protein sequences"""

    def __init__(self, config: DatabaseConfig, email: str):
        super().__init__(config, email)
        self.base_url = "https://rest.uniprot.org"

    def search(self, criteria: SearchCriteria) -> List[str]:
        """Query the UniProt database"""
        logger.info("Searching UniProt database...")

        query_parts = []

        if criteria.organism:
            query_parts.append(f'organism:"{criteria.organism}"')

        if criteria.keywords:
            keyword_query = " OR ".join(criteria.keywords)
            query_parts.append(f"({keyword_query})")

        if criteria.min_length:
            query_parts.append(f"length:[{criteria.min_length} TO *]")

        if criteria.max_length:
            query_parts.append(f"length:[* TO {criteria.max_length}]")

        query = " AND ".join(query_parts)

        try:
            url = f"{self.base_url}/uniprotkb/search"
            params = {
                "query": query,
                "format": "tsv",
                "fields": "accession",
                "size": min(criteria.max_results, 500),  # UniProt limit
            }

            response = self.session.get(url, params=params, timeout=self.config.timeout)
            response.raise_for_status()

            # Parse results
            lines = response.text.strip().split("\n")[1:]  # Skip header
            ids = [line.strip() for line in lines if line.strip()]

            logger.info(f"Found {len(ids)} UniProt entries")
            return ids

        except Exception as exc:
            logger.error(f"Error searching UniProt: {exc}")
            return []

    def fetch_metadata(self, ids: List[str]) -> List[Dict[str, Any]]:
        """Fetch metadata for UniProt entries."""
        logger.info(f"Fetching UniProt metadata for {len(ids)} entries...")

        metadata_list = []
        batch_size = min(self.config.batch_size, 25)  # UniProt batch limit

        for i in range(0, len(ids), batch_size):
            batch = ids[i : i + batch_size]

            try:
                url = f"{self.base_url}/uniprotkb/accessions"
                params = {
                    "accessions": ",".join(batch),
                    "format": "tsv",
                    "fields": "accession,id,protein_name,organism_name,length,date_created,date_modified,taxonomy_id",
                }

                response = self.session.get(
                    url, params=params, timeout=self.config.timeout
                )
                response.raise_for_status()

                # Parse TSV response
                lines = response.text.strip().split("\n")
                headers = lines[0].split("\t")

                for line in lines[1:]:
                    values = line.split("\t")
                    if len(values) >= len(headers):
                        metadata_list.append(
                            {
                                "id": values[0],
                                "accession": values[0],
                                "title": values[2] if len(values) > 2 else "",
                                "organism": values[3] if len(values) > 3 else "",
                                "length": int(values[4])
                                if len(values) > 4 and values[4].isdigit()
                                else 0,
                                "create_date": values[5] if len(values) > 5 else "",
                                "update_date": values[6] if len(values) > 6 else "",
                                "taxonomy_id": values[7] if len(values) > 7 else "",
                                "database": "UniProt",
                            }
                        )

                time.sleep(self.config.rate_limit)

            except Exception as exc:
                logger.warning(
                    f"Error fetching UniProt metadata for batch {i//batch_size + 1}: {exc}"
                )
                continue

        logger.info(f"Retrieved metadata for {len(metadata_list)} UniProt entries")
        return metadata_list

    def download(self, ids: List[str], outdir: Path) -> List[Dict[str, Any]]:
        """Download sequences from UniProt."""
        logger.info(f"Attempting to download {len(ids)} UniProt sequences...")

        downloaded_sequences = []

        for uniprot_id in ids:
            try:
                url = f"{self.base_url}/uniprotkb/{uniprot_id}.fasta"
                response = self.session.get(url, timeout=self.config.timeout)
                response.raise_for_status()

                fasta_data = StringIO(response.text)
                record = SeqIO.read(fasta_data, "fasta")

                seq_info = {
                    "id": uniprot_id,
                    "accession": record.id,
                    "description": record.description,
                    "sequence_length": len(record.seq),
                    "sequence": str(record.seq),
                    "downloaded": True,
                }

                downloaded_sequences.append(seq_info)
                logger.debug(f"Downloaded {record.id} ({len(record.seq)} aa)")

                time.sleep(self.config.rate_limit)

            except Exception as e:
                logger.warning(f"Failed to download {uniprot_id}: {e}")
                continue

        logger.info(
            f"Successfully downloaded {len(downloaded_sequences)} UniProt sequences"
        )
        return downloaded_sequences
