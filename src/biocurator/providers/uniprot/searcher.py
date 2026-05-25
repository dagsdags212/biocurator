import logging
import time
from io import StringIO
from pathlib import Path
from typing import Iterator

from requests import Session

from Bio import SeqIO
from tenacity import (
    Retrying,
    before_sleep_log,
    stop_after_attempt,
    wait_exponential,
)

from biocurator.config.schema import RetryConfig
from biocurator.exceptions import DatabaseSearchError
from biocurator.providers.base import DatabaseConfig, DatabaseSearcher, SequenceRecord
from biocurator.providers.uniprot.criteria import UniProtSearchCriteria
from biocurator.providers.uniprot.query_builders import UniProtQueryBuilder
from biocurator.providers.registry import ProviderRegistry
from biocurator.utils.logging import get_logger
from biocurator.utils.retryable_exceptions import RETRYABLE_PREDICATE

logger = get_logger(__name__)


class UniProtSearcher(DatabaseSearcher[UniProtSearchCriteria]):
    session: Session

    def __init__(self, config: DatabaseConfig, email: str) -> None:
        super().__init__(config, email)
        self._base_url = "https://rest.uniprot.org"
        self.session = Session()

    def _make_retryer(self) -> Retrying:
        retry_cfg = (
            self.config.retry.resolve() if self.config.retry else RetryConfig.defaults()
        )
        return Retrying(
            stop=stop_after_attempt(retry_cfg.max_attempts),
            wait=wait_exponential(
                multiplier=retry_cfg.backoff_factor,
                max=retry_cfg.max_delay,
            ),
            retry=RETRYABLE_PREDICATE,
            reraise=True,
            before_sleep=before_sleep_log(logger, logging.WARNING),
        )

    def _safe_get(self, url: str, **kwargs):
        """Execute an HTTP GET with retry logic.

        Only the HTTP call and raise_for_status() are inside the retry block,
        so 5xx responses are retried while 4xx are not. Response body parsing
        (response.text) happens outside the retry.
        """
        retryer = self._make_retryer()
        response = retryer(self.session.get, url, **kwargs)
        response.raise_for_status()
        return response

    def build_query(self, criteria: UniProtSearchCriteria) -> str:
        return UniProtQueryBuilder().build(criteria)

    def search(self, criteria: UniProtSearchCriteria) -> list[str]:
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
            response = self._safe_get(url, params=params, timeout=self.config.timeout)
            lines = response.text.strip().split("\n")[1:]
            ids = [line.strip() for line in lines if line.strip()]
            logger.info(f"Found {len(ids)} UniProt entries")
            return ids
        except DatabaseSearchError:
            raise
        except Exception as exc:
            raise DatabaseSearchError(f"UniProt search error: {exc}") from exc

    def fetch_metadata(
        self, ids: list[str], criteria: UniProtSearchCriteria | None = None
    ) -> Iterator[SequenceRecord]:
        logger.info(f"Streaming UniProt metadata for {len(ids)} entries...")
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
                response = self._safe_get(
                    url, params=params, timeout=self.config.timeout
                )
                lines = response.text.strip().split("\n")
                headers = lines[0].split("\t")
                for line in lines[1:]:
                    values = line.split("\t")
                    if len(values) >= len(headers):
                        yield SequenceRecord(
                            id=values[0],
                            accession=values[0],
                            title=values[2] if len(values) > 2 else "",
                            organism=values[3] if len(values) > 3 else "",
                            sequence_length=(
                                int(values[4])
                                if len(values) > 4 and values[4].isdigit()
                                else 0
                            ),
                            create_date=values[5] if len(values) > 5 else "",
                            update_date=values[6] if len(values) > 6 else "",
                            taxonomy_id=values[7] if len(values) > 7 else "",
                            database="UniProt",
                        )
                time.sleep(self.config.rate_limit)
            except Exception as exc:
                logger.warning(
                    f"Error fetching UniProt metadata for batch {i // batch_size + 1}: {exc}"
                )

    def download(
        self,
        ids: list[str],
        outdir: Path,
        criteria: UniProtSearchCriteria | None = None,
    ) -> Iterator[SequenceRecord]:
        logger.info(f"Attempting to stream download {len(ids)} UniProt sequences...")
        for uid in ids:
            try:
                url = f"{self._base_url}/uniprotkb/{uid}.fasta"
                response = self._safe_get(url, timeout=self.config.timeout)
                record = SeqIO.read(StringIO(response.text), "fasta")
                yield SequenceRecord(
                    id=uid,
                    accession=record.id,
                    description=record.description,
                    sequence_length=len(record.seq),
                    sequence=str(record.seq),
                    database="UniProt",
                    downloaded=True,
                )
                logger.debug(f"Downloaded {record.id} ({len(record.seq)} aa)")
                time.sleep(self.config.rate_limit)
            except Exception as exc:
                logger.warning(f"Failed to download {uid}: {exc}")


ProviderRegistry.register("uniprot", UniProtSearcher)
