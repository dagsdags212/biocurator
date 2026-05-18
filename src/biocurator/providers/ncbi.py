import time
from io import StringIO
from pathlib import Path
from typing import Any

from Bio import Entrez, SeqIO

from biocurator.providers.base import DatabaseConfig, DatabaseSearcher, SearchCriteria
from biocurator.providers.registry import ProviderRegistry
from biocurator.utils.logging import get_logger

logger = get_logger(__name__)


class NCBISearcher(DatabaseSearcher):
    def __init__(self, config: DatabaseConfig, email: str) -> None:
        super().__init__(config, email)
        Entrez.email = email
        Entrez.tool = "Biocurator"
        if config.api_key:
            Entrez.api_key = config.api_key
        self._db_mapping = {
            "nucleotide": "nucleotide",
            "protein": "protein",
            "sra": "sra",
        }

    def build_query(self, criteria: SearchCriteria) -> str:
        parts = []
        if criteria.organism:
            parts.append(f'"{criteria.organism}"[Organism]')
        if criteria.keywords:
            parts.append(" OR ".join(f'"{kw}"' for kw in criteria.keywords))
        if criteria.location:
            loc_terms = [f'"{t.strip()}"' for t in criteria.location.split(",")]
            parts.append(" OR ".join(loc_terms))
        if criteria.min_length and criteria.max_length:
            parts.append(f"{criteria.min_length}:{criteria.max_length}[Sequence Length]")
        elif criteria.min_length:
            parts.append(f"{criteria.min_length}:999999999[Sequence Length]")
        elif criteria.max_length:
            parts.append(f"1:{criteria.max_length}[Sequence Length]")
        if criteria.start_date and criteria.end_date:
            parts.append(
                f'"{criteria.start_date}"[Publication Date]:"{criteria.end_date}"[Publication Date]'
            )
        if criteria.taxonomy_filter:
            parts.append(f'"{criteria.taxonomy_filter}"[Organism]')
        for term in criteria.exclude_terms:
            parts.append(f'NOT "{term}"')
        return " AND ".join(parts)

    def search(self, criteria: SearchCriteria) -> list[str]:
        logger.info(f"Searching NCBI {criteria.sequence_type} database...")
        query = self.build_query(criteria)
        logger.info(f"Search query: {query}")
        try:
            db = self._db_mapping.get(criteria.sequence_type, "nucleotide")
            handle = Entrez.esearch(db=db, term=query, retmax=criteria.max_results, sort="relevance")
            results = Entrez.read(handle)
            handle.close()
            ids = results["IdList"]
            logger.info(f"Found {len(ids)} potential sequences")
            return ids
        except Exception as exc:
            logger.error(f"Error searching NCBI: {exc}")
            return []

    def fetch_metadata(self, ids: list[str]) -> list[dict[str, Any]]:
        logger.info(f"Fetching metadata for {len(ids)} sequences...")
        metadata_list = []
        for i in range(0, len(ids), self.config.batch_size):
            batch = ids[i : i + self.config.batch_size]
            try:
                handle = Entrez.esummary(db="nucleotide", id=",".join(batch))
                summaries = Entrez.read(handle)
                handle.close()
                for s in summaries:
                    metadata_list.append({
                        "id": s.get("Id", ""),
                        "accession": s.get("AccessionVersion", ""),
                        "title": s.get("Title", ""),
                        "organism": s.get("Organism", ""),
                        "sequence_length": int(s.get("Length", 0)),
                        "create_date": s.get("CreateDate", ""),
                        "update_date": s.get("UpdateDate", ""),
                        "authors": s.get("AuthorList", ""),
                        "journal": s.get("Source", ""),
                        "taxonomy_id": s.get("TaxId", ""),
                        "database": "NCBI",
                    })
                time.sleep(self.config.rate_limit)
            except Exception as exc:
                logger.warning(f"Error fetching metadata for batch {i // self.config.batch_size + 1}: {exc}")
        logger.info(f"Retrieved metadata for {len(metadata_list)} sequences")
        return metadata_list

    def download(self, ids: list[str], outdir: Path) -> list[dict[str, Any]]:
        logger.info(f"Attempting to download {len(ids)} sequences...")
        downloaded = []
        for seq_id in ids:
            try:
                handle = Entrez.efetch(db="nucleotide", id=seq_id, rettype="fasta", retmode="text")
                record = SeqIO.read(handle, "fasta")
                handle.close()
                downloaded.append({
                    "id": seq_id,
                    "accession": record.id,
                    "description": record.description,
                    "sequence_length": len(record.seq),
                    "sequence": str(record.seq),
                    "downloaded": True,
                })
                logger.debug(f"Downloaded {record.id} ({len(record.seq)} bp)")
                time.sleep(self.config.rate_limit)
            except Exception as exc:
                logger.warning(f"Failed to download {seq_id}: {exc}")
        logger.info(f"Successfully downloaded {len(downloaded)} sequences")
        return downloaded


ProviderRegistry.register("ncbi", NCBISearcher)
