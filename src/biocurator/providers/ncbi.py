import time
from pathlib import Path

from Bio import Entrez, SeqIO

from biocurator.providers.base import DatabaseConfig, DatabaseSearcher, NCBIDatabase, SequenceRecord
from biocurator.providers.ncbi_criteria import NCBISearchCriteria
from biocurator.providers.ncbi_query_builders import get_builder
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

    def build_query(self, criteria: NCBISearchCriteria) -> str:  # type: ignore[override]
        return get_builder(criteria.database).build(criteria)

    def search(self, criteria: NCBISearchCriteria) -> list[str]:  # type: ignore[override]
        logger.info(f"Searching NCBI {criteria.database} database...")
        query = self.build_query(criteria)
        logger.info(f"Search query: {query}")
        try:
            handle = Entrez.esearch(
                db=criteria.database, term=query, retmax=criteria.max_results, sort="relevance"
            )
            results = Entrez.read(handle)
            handle.close()
            ids = results["IdList"]
            logger.info(f"Found {len(ids)} potential sequences")
            return ids
        except Exception as exc:
            logger.error(f"Error searching NCBI: {exc}")
            return []

    def fetch_metadata(self, ids: list[str], criteria: NCBISearchCriteria | None = None) -> list[SequenceRecord]:
        db = criteria.database if criteria else NCBIDatabase.NUCCORE
        logger.info(f"Fetching metadata for {len(ids)} sequences...")
        metadata_list = []
        for i in range(0, len(ids), self.config.batch_size):
            batch = ids[i : i + self.config.batch_size]
            try:
                handle = Entrez.esummary(db=db, id=",".join(batch))
                summaries = Entrez.read(handle)
                handle.close()
                for s in summaries:
                    metadata_list.append(
                        SequenceRecord(
                            id=str(s.get("Id", "")),
                            accession=str(s.get("AccessionVersion", "")),
                            title=str(s.get("Title", "")),
                            organism=str(s.get("Organism", "")),
                            sequence_length=int(s.get("Length", 0)),
                            create_date=str(s.get("CreateDate", "")),
                            update_date=str(s.get("UpdateDate", "")),
                            authors=str(s.get("AuthorList", "")),
                            journal=str(s.get("Source", "")),
                            taxonomy_id=str(s.get("TaxId", "")),
                            database="NCBI",
                        )
                    )
                time.sleep(self.config.rate_limit)
            except Exception as exc:
                logger.warning(
                    f"Error fetching metadata for batch {i // self.config.batch_size + 1}: {exc}"
                )
        logger.info(f"Retrieved metadata for {len(metadata_list)} sequences")
        return metadata_list

    def download(self, ids: list[str], outdir: Path, criteria: NCBISearchCriteria | None = None) -> list[SequenceRecord]:
        db = criteria.database if criteria else NCBIDatabase.NUCCORE
        logger.info(f"Attempting to download {len(ids)} sequences...")
        downloaded = []
        for seq_id in ids:
            try:
                handle = Entrez.efetch(
                    db=db, id=seq_id, rettype="fasta", retmode="text"
                )
                record = SeqIO.read(handle, "fasta")
                handle.close()
                downloaded.append(
                    SequenceRecord(
                        id=seq_id,
                        accession=record.id,
                        description=record.description,
                        sequence_length=len(record.seq),
                        sequence=str(record.seq),
                        database="NCBI",
                        downloaded=True,
                    )
                )
                logger.debug(f"Downloaded {record.id} ({len(record.seq)} bp)")
                time.sleep(self.config.rate_limit)
            except Exception as exc:
                logger.warning(f"Failed to download {seq_id}: {exc}")
        logger.info(f"Successfully downloaded {len(downloaded)} sequences")
        return downloaded


ProviderRegistry.register("ncbi", NCBISearcher)
