import time
from io import StringIO
from pathlib import Path
from typing import Any

from requests import Session

from Bio import SeqIO

from biocurator.providers.base import DatabaseConfig, DatabaseSearcher, SearchCriteria
from biocurator.providers.registry import ProviderRegistry
from biocurator.utils.logging import get_logger

logger = get_logger(__name__)


class UniProtSearcher(DatabaseSearcher):
    session: Session

    def __init__(self, config: DatabaseConfig, email: str) -> None:
        super().__init__(config, email)
        self._base_url = "https://rest.uniprot.org"
        self.session = Session()

    def build_query(self, criteria: SearchCriteria) -> str:
        parts = []
        if criteria.organism:
            parts.append(f'organism:"{criteria.organism}"')
        if criteria.keywords:
            parts.append("(" + " OR ".join(criteria.keywords) + ")")
        if criteria.min_length:
            parts.append(f"length:[{criteria.min_length} TO *]")
        if criteria.max_length:
            parts.append(f"length:[* TO {criteria.max_length}]")
        return " AND ".join(parts)

    def search(self, criteria: SearchCriteria) -> list[str]:
        logger.info("Searching UniProt database...")
        query = self.build_query(criteria)
        try:
            url = f"{self._base_url}/uniprotkb/search"
            params = {
                "query": query,
                "format": "tsv",
                "fields": "accession",
                "size": min(criteria.max_results, 500),
            }
            response = self.session.get(url, params=params, timeout=self.config.timeout)
            response.raise_for_status()
            lines = response.text.strip().split("\n")[1:]
            ids = [line.strip() for line in lines if line.strip()]
            logger.info(f"Found {len(ids)} UniProt entries")
            return ids
        except Exception as exc:
            logger.error(f"Error searching UniProt: {exc}")
            return []

    def fetch_metadata(self, ids: list[str]) -> list[dict[str, Any]]:
        logger.info(f"Fetching UniProt metadata for {len(ids)} entries...")
        metadata_list = []
        batch_size = min(self.config.batch_size, 25)
        for i in range(0, len(ids), batch_size):
            batch = ids[i : i + batch_size]
            try:
                url = f"{self._base_url}/uniprotkb/accessions"
                params = {
                    "accessions": ",".join(batch),
                    "format": "tsv",
                    "fields": "accession,id,protein_name,organism_name,length,date_created,date_modified,taxonomy_id",
                }
                response = self.session.get(url, params=params, timeout=self.config.timeout)
                response.raise_for_status()
                lines = response.text.strip().split("\n")
                headers = lines[0].split("\t")
                for line in lines[1:]:
                    values = line.split("\t")
                    if len(values) >= len(headers):
                        metadata_list.append({
                            "id": values[0],
                            "accession": values[0],
                            "title": values[2] if len(values) > 2 else "",
                            "organism": values[3] if len(values) > 3 else "",
                            "sequence_length": int(values[4]) if len(values) > 4 and values[4].isdigit() else 0,
                            "create_date": values[5] if len(values) > 5 else "",
                            "update_date": values[6] if len(values) > 6 else "",
                            "taxonomy_id": values[7] if len(values) > 7 else "",
                            "database": "UniProt",
                        })
                time.sleep(self.config.rate_limit)
            except Exception as exc:
                logger.warning(f"Error fetching UniProt metadata for batch {i // batch_size + 1}: {exc}")
        logger.info(f"Retrieved metadata for {len(metadata_list)} UniProt entries")
        return metadata_list

    def download(self, ids: list[str], outdir: Path) -> list[dict[str, Any]]:
        logger.info(f"Attempting to download {len(ids)} UniProt sequences...")
        downloaded = []
        for uid in ids:
            try:
                url = f"{self._base_url}/uniprotkb/{uid}.fasta"
                response = self.session.get(url, timeout=self.config.timeout)
                response.raise_for_status()
                record = SeqIO.read(StringIO(response.text), "fasta")
                downloaded.append({
                    "id": uid,
                    "accession": record.id,
                    "description": record.description,
                    "sequence_length": len(record.seq),
                    "sequence": str(record.seq),
                    "downloaded": True,
                })
                logger.debug(f"Downloaded {record.id} ({len(record.seq)} aa)")
                time.sleep(self.config.rate_limit)
            except Exception as exc:
                logger.warning(f"Failed to download {uid}: {exc}")
        logger.info(f"Successfully downloaded {len(downloaded)} UniProt sequences")
        return downloaded


ProviderRegistry.register("uniprot", UniProtSearcher)
