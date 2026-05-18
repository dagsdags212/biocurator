import time
from dataclasses import dataclass
from io import StringIO
from pathlib import Path

from requests import Session

from Bio import SeqIO

from biocurator.providers.base import DatabaseConfig, DatabaseSearcher, QueryBuilder, SearchCriteria, SequenceRecord
from biocurator.providers.registry import ProviderRegistry
from biocurator.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class UniProtSearchCriteria(SearchCriteria):
    reviewed: bool | None = None


class UniProtQueryBuilder(QueryBuilder["UniProtSearchCriteria"]):
    def build(self, criteria: "UniProtSearchCriteria") -> str:
        parts = []
        if criteria.organism:
            parts.append(f'organism:"{criteria.organism}"')
        if criteria.keywords:
            parts.append("(" + " OR ".join(criteria.keywords) + ")")
        if criteria.min_length:
            parts.append(f"length:[{criteria.min_length} TO *]")
        if criteria.max_length:
            parts.append(f"length:[* TO {criteria.max_length}]")
        if criteria.reviewed is not None:
            parts.append(f"reviewed:{'true' if criteria.reviewed else 'false'}")
        return " AND ".join(parts)

    def available_fields(self) -> dict[str, str]:
        return {
            "accession": "UniProtKB accession number",
            "id": "UniProtKB entry name",
            "organism_name": "Scientific name of the organism",
            "organism_id": "NCBI taxonomy identifier",
            "gene_names": "Gene name(s)",
            "protein_name": "Recommended protein name",
            "length": "Sequence length in amino acids",
            "reviewed": "Reviewed (Swiss-Prot) or unreviewed (TrEMBL)",
            "keyword": "UniProt controlled vocabulary keyword",
            "go": "Gene Ontology term",
            "ec": "Enzyme Commission number",
            "ft_sites": "Annotated sites (active site, binding site, etc.)",
            "database": "Cross-references to external databases",
            "date_created": "Date the entry was created",
            "date_modified": "Date the entry was last modified",
            "date_sequence_modified": "Date the sequence was last modified",
            "mass": "Molecular mass in Daltons",
            "cc_subcellular_location": "Subcellular location",
            "cc_tissue_specificity": "Tissue specificity",
            "cc_disease": "Disease involvement",
            "taxonomy_id": "Taxonomic lineage identifier",
            "lineage": "Full taxonomic lineage",
            "strain": "Organism strain",
            "fragment": "Whether sequence is a fragment",
        }


class UniProtSearcher(DatabaseSearcher):
    session: Session

    def __init__(self, config: DatabaseConfig, email: str) -> None:
        super().__init__(config, email)
        self._base_url = "https://rest.uniprot.org"
        self.session = Session()

    def build_query(self, criteria: UniProtSearchCriteria) -> str:  # type: ignore[override]
        return UniProtQueryBuilder().build(criteria)

    def search(self, criteria: UniProtSearchCriteria) -> list[str]:  # type: ignore[override]
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

    def fetch_metadata(self, ids: list[str], criteria: SearchCriteria | None = None) -> list[SequenceRecord]:
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
                        metadata_list.append(SequenceRecord(
                            id=values[0],
                            accession=values[0],
                            title=values[2] if len(values) > 2 else "",
                            organism=values[3] if len(values) > 3 else "",
                            sequence_length=int(values[4]) if len(values) > 4 and values[4].isdigit() else 0,
                            create_date=values[5] if len(values) > 5 else "",
                            update_date=values[6] if len(values) > 6 else "",
                            taxonomy_id=values[7] if len(values) > 7 else "",
                            database="UniProt",
                        ))
                time.sleep(self.config.rate_limit)
            except Exception as exc:
                logger.warning(f"Error fetching UniProt metadata for batch {i // batch_size + 1}: {exc}")
        logger.info(f"Retrieved metadata for {len(metadata_list)} UniProt entries")
        return metadata_list

    def download(self, ids: list[str], outdir: Path, criteria: SearchCriteria | None = None) -> list[SequenceRecord]:
        logger.info(f"Attempting to download {len(ids)} UniProt sequences...")
        downloaded = []
        for uid in ids:
            try:
                url = f"{self._base_url}/uniprotkb/{uid}.fasta"
                response = self.session.get(url, timeout=self.config.timeout)
                response.raise_for_status()
                record = SeqIO.read(StringIO(response.text), "fasta")
                downloaded.append(SequenceRecord(
                    id=uid,
                    accession=record.id,
                    description=record.description,
                    sequence_length=len(record.seq),
                    sequence=str(record.seq),
                    database="UniProt",
                    downloaded=True,
                ))
                logger.debug(f"Downloaded {record.id} ({len(record.seq)} aa)")
                time.sleep(self.config.rate_limit)
            except Exception as exc:
                logger.warning(f"Failed to download {uid}: {exc}")
        logger.info(f"Successfully downloaded {len(downloaded)} UniProt sequences")
        return downloaded


ProviderRegistry.register("uniprot", UniProtSearcher)
