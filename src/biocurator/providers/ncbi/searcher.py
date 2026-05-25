import logging
import time
from pathlib import Path
from typing import Iterator, Any, Callable

from Bio import Entrez, SeqIO
from Bio.SeqRecord import SeqRecord as BioSeqRecord
from tenacity import (
    Retrying,
    before_sleep_log,
    stop_after_attempt,
    wait_exponential,
)

from biocurator.config.schema import RetryConfig
from biocurator.exceptions import DatabaseSearchError
from biocurator.providers.base import (
    DatabaseConfig,
    DatabaseSearcher,
    NCBIDatabase,
    SequenceRecord,
)
from biocurator.providers.ncbi.criteria import NCBISearchCriteria
from biocurator.providers.ncbi.query_builders import get_builder
from biocurator.providers.registry import ProviderRegistry
from biocurator.utils.logging import get_logger
from biocurator.utils.retryable_exceptions import RETRYABLE_PREDICATE

logger = get_logger(__name__)


class NCBISearcher(DatabaseSearcher[NCBISearchCriteria]):
    def __init__(self, config: DatabaseConfig, email: str) -> None:
        super().__init__(config, email)
        Entrez.email = email
        Entrez.tool = "Biocurator"
        if config.api_key:
            Entrez.api_key = config.api_key

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

    def _safe_entrez_call(self, func: Callable, **kwargs) -> Any:
        """Execute an Entrez HTTP call with retry logic.

        Only the HTTP call (func(**kwargs)) is retried.
        Parse errors from Entrez.read() are NOT retried.
        """
        retryer = self._make_retryer()
        handle = retryer(func, **kwargs)
        try:
            return Entrez.read(handle)
        finally:
            handle.close()

    def _fetch_single(self, params: dict) -> BioSeqRecord:
        """Fetch a single sequence with retry. Parse outside retry."""
        retryer = self._make_retryer()
        handle = retryer(Entrez.efetch, **params)
        try:
            return SeqIO.read(handle, "fasta")
        finally:
            handle.close()

    def build_query(self, criteria: NCBISearchCriteria) -> str:
        return get_builder(criteria.database).build(criteria)

    def search(self, criteria: NCBISearchCriteria) -> list[str]:
        logger.info(f"Searching NCBI {criteria.database} database...")
        query = self.build_query(criteria)
        logger.info(f"Search query: {query}")
        try:
            results = self._safe_entrez_call(
                Entrez.esearch,
                db=criteria.database,
                term=query,
                retmax=criteria.max_results,
                sort="relevance",
                usehistory="y",
            )

            ids = results.get("IdList", [])
            criteria.webenv = results.get("WebEnv")
            criteria.query_key = results.get("QueryKey")

            logger.info(f"Found {len(ids)} potential sequences (History Server active)")
            return ids
        except DatabaseSearchError:
            raise
        except Exception as exc:
            raise DatabaseSearchError(f"NCBI search error: {exc}") from exc

    def fetch_metadata(
        self, ids: list[str], criteria: NCBISearchCriteria | None = None
    ) -> Iterator[SequenceRecord]:
        db = criteria.database if criteria else NCBIDatabase.NUCCORE
        webenv = criteria.webenv if criteria else None
        query_key = criteria.query_key if criteria else None

        count = len(ids)
        logger.info(f"Streaming metadata for {count} sequences...")

        for i in range(0, count, self.config.batch_size):
            batch_size = min(self.config.batch_size, count - i)
            try:
                params = {
                    "db": db,
                    "retstart": i,
                    "retmax": batch_size,
                }
                if webenv and query_key:
                    params.update({"WebEnv": webenv, "query_key": query_key})
                else:
                    params["id"] = ",".join(ids[i : i + batch_size])

                summaries = self._safe_entrez_call(Entrez.esummary, **params)

                for s in summaries:
                    yield SequenceRecord(
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
                time.sleep(self.config.rate_limit)
            except Exception as exc:
                logger.warning(
                    f"Error fetching metadata for batch {i // self.config.batch_size + 1}: {exc}"
                )

    def download(
        self, ids: list[str], outdir: Path, criteria: NCBISearchCriteria | None = None
    ) -> Iterator[SequenceRecord]:
        db = criteria.database if criteria else NCBIDatabase.NUCCORE
        webenv = criteria.webenv if criteria else None
        query_key = criteria.query_key if criteria else None

        count = len(ids)
        logger.info(f"Attempting to stream download {count} sequences...")

        for i in range(count):
            try:
                params = {
                    "db": db,
                    "rettype": "fasta",
                    "retmode": "text",
                }
                if webenv and query_key:
                    params.update(
                        {
                            "WebEnv": webenv,
                            "query_key": query_key,
                            "retstart": i,
                            "retmax": 1,
                        }
                    )
                else:
                    params["id"] = ids[i]

                record = self._fetch_single(params)

                yield SequenceRecord(
                    id=ids[i] if not (webenv and query_key) else record.id,
                    accession=record.id,
                    description=record.description,
                    sequence_length=len(record.seq),
                    sequence=str(record.seq),
                    database="NCBI",
                    downloaded=True,
                )
                logger.debug(f"Downloaded {record.id} ({len(record.seq)} bp)")
                time.sleep(self.config.rate_limit)
            except Exception as exc:
                logger.warning(f"Failed to download sequence at index {i}: {exc}")


ProviderRegistry.register("ncbi", NCBISearcher)
