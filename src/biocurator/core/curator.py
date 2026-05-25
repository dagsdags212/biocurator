"""
Biocurator Module
====================

This module contains the main Biocurator class that coordinates
sequence search, download, filtering, and organization.


© Jan Emmanuel Samson (2026-)
"""

import pandas as pd
from pathlib import Path
from typing import Optional

from biocurator.config.schema import BreakerConfig, RetryConfig
from biocurator.providers import ProviderRegistry, DatabaseConfig, SearchCriteria
from biocurator.providers.health import HealthChecker
from biocurator.providers.ncbi import NCBISearchCriteria
from biocurator.providers.uniprot import UniProtSearchCriteria
from .filters import SequenceFilter
from ..utils.logging import get_logger

# Get logger for this module
logger = get_logger(__name__)


class Biocurator:
    """Main Biocurator class for biological dataset curation."""

    def __init__(
        self,
        email: str,
        outdir: Optional[str] = None,
        global_retry: RetryConfig | None = None,
        global_breaker: BreakerConfig | None = None,
    ) -> None:
        """Initialize BioCurator.

        Parameters
        ----------
        email : str
            Email address for database access
        outdir : str, optional
            Output directory for results
        global_retry : RetryConfig, optional
            Global retry configuration from the config file
        global_breaker : BreakerConfig, optional
            Global circuit breaker configuration from the config file
        """
        logger.info("Initializing Biocurator")
        self.email = email
        self.outdir = Path(outdir) if outdir else Path("biocurator_output")
        self.global_retry = global_retry
        self.global_breaker = global_breaker
        self.searchers: dict = {}
        self._init_database_searchers()
        logger.info("Biocurator initialization complete")

    def _init_database_searchers(self) -> None:
        logger.info("Initializing database searchers")
        ncbi_cfg = DatabaseConfig(
            name="NCBI",
            rate_limit=0.3,
            batch_size=20,
            retry=self.global_retry,
            breaker=self.global_breaker,
        )
        self.searchers["ncbi"] = ProviderRegistry.get("ncbi", ncbi_cfg, self.email)
        uniprot_cfg = DatabaseConfig(
            name="UniProt",
            base_url="https://rest.uniprot.org",
            rate_limit=0.5,
            batch_size=25,
            retry=self.global_retry,
            breaker=self.global_breaker,
        )
        self.searchers["uniprot"] = ProviderRegistry.get(
            "uniprot", uniprot_cfg, self.email
        )
        logger.info(f"Database searchers initialized: {list(self.searchers.keys())}")

    def get_health_status(self) -> list[dict]:
        """Probe all configured database providers and return health statuses.

        Returns
        -------
        list[dict]
            Each dict has keys: provider, status, response_time_ms, breaker_state, error.
        """
        statuses = []
        for name, searcher in self.searchers.items():
            searcher_cfg = searcher.config
            timeout = searcher_cfg.timeout if hasattr(searcher_cfg, "timeout") else 30
            breaker = (
                searcher.breaker_state if hasattr(searcher, "breaker_state") else None
            )

            if name == "ncbi":
                result = HealthChecker.ping_ncbi(timeout=timeout)
            elif name == "uniprot":
                result = HealthChecker.ping_uniprot(timeout=timeout)
            else:
                statuses.append(
                    {
                        "provider": name,
                        "status": "UNKNOWN",
                        "response_time_ms": 0.0,
                        "breaker_state": breaker,
                        "error": f"No health check for provider: {name}",
                    }
                )
                continue

            statuses.append(
                {
                    "provider": result.provider,
                    "status": "UP" if result.reachable else "DOWN",
                    "response_time_ms": result.response_time_ms,
                    "breaker_state": breaker,
                    "error": result.error,
                }
            )

        return statuses

    def run_job(self, job_config, progress_callback=None) -> dict:
        """Run a single curation job from a JobConfig.

        Parameters
        ----------
        job_config : JobConfig
            Typed config for this job.
        progress_callback : callable, optional
            Called as callback(phase, current, total) after each phase.

        Returns
        -------
        dict
            Mapping of format name to output file Path.
        """
        from .exporter import StreamingExporter

        def _report(phase, current, total):
            if progress_callback:
                progress_callback(phase, current, total)

        export_config = job_config.export
        outdir = Path(export_config.outdir)

        with StreamingExporter(
            outdir, export_config.prefix, export_config.formats
        ) as exporter:
            for db_name in job_config.search.databases:
                if db_name not in self.searchers:
                    logger.warning(f"Database '{db_name}' not configured, skipping")
                    continue

                searcher = self.searchers[db_name]

                base = (
                    self.global_retry.resolve()
                    if self.global_retry
                    else RetryConfig.defaults()
                )
                per_db = (
                    job_config.search.retry.get(db_name)
                    if job_config.search.retry
                    else None
                )
                searcher.config.retry = per_db.resolve(base) if per_db else base

                # Merge breaker config: per-database override > global > pybreaker defaults
                base_breaker = (
                    self.global_breaker.resolve()
                    if self.global_breaker
                    else BreakerConfig.defaults()
                )
                per_db_breaker = (
                    job_config.search.breaker.get(db_name)
                    if job_config.search and job_config.search.breaker
                    else None
                )
                searcher.config.breaker = (
                    per_db_breaker.resolve(base_breaker)
                    if per_db_breaker
                    else base_breaker
                )
                searcher._breaker = searcher._init_breaker()
                per_db_breaker = (
                    job_config.search.breaker.get(db_name)
                    if job_config.search and job_config.search.breaker
                    else None
                )
                searcher.config.breaker = (
                    per_db_breaker.resolve(base_breaker)
                    if per_db_breaker
                    else base_breaker
                )

                search_cfg = job_config.search
                filter_cfg = job_config.filter

                common_kwargs = dict(
                    organism=search_cfg.organism,
                    keywords=search_cfg.keywords,
                    min_length=filter_cfg.min_length,
                    max_length=filter_cfg.max_length,
                    max_results=search_cfg.max_results,
                    exclude_terms=filter_cfg.exclude_terms,
                    quality_threshold=filter_cfg.quality_threshold,
                    start_date=search_cfg.date_range.get("start")
                    if search_cfg.date_range
                    else None,
                    end_date=search_cfg.date_range.get("end")
                    if search_cfg.date_range
                    else None,
                )
                if db_name == "ncbi":
                    from biocurator.providers.base import NCBIDatabase as _NCBIDb

                    criteria = NCBISearchCriteria(
                        database=_NCBIDb.NUCCORE, **common_kwargs
                    )
                elif db_name == "uniprot":
                    criteria = UniProtSearchCriteria(**common_kwargs)
                else:
                    criteria = SearchCriteria(**common_kwargs)

                ids = searcher.search(criteria)
                total_found = len(ids)
                _report("search", total_found, total_found)

                if not ids:
                    continue

                # Stream metadata and filter
                logger.info(
                    f"Filtering metadata for {total_found} potential matches..."
                )
                metadata_generator = searcher.fetch_metadata(ids, criteria)

                filtered_metadata_ids = []

                processed_count = 0
                for record in metadata_generator:
                    processed_count += 1
                    # Apply metadata filters (length, organism, exclude terms)
                    passed = SequenceFilter.filter_by_criteria([record], criteria)
                    if passed:
                        filtered_metadata_ids.append(record.id)

                    if processed_count % 10 == 0 or processed_count == total_found:
                        _report("filter", processed_count, total_found)

                total_filtered = len(filtered_metadata_ids)
                logger.info(
                    f"Filtering complete: {total_filtered}/{total_found} records passed."
                )

                if not filtered_metadata_ids:
                    continue

                # Stream download and final quality check
                logger.info(f"Downloading {total_filtered} filtered sequences...")
                download_generator = searcher.download(
                    filtered_metadata_ids, outdir, criteria
                )

                download_count = 0
                for seq_record in download_generator:
                    download_count += 1
                    # Apply sequence-level quality filter
                    if criteria.quality_threshold:
                        passed = SequenceFilter.apply_quality_filter(
                            [seq_record], criteria.quality_threshold
                        )
                        if not passed:
                            _report("download", download_count, total_filtered)
                            continue

                    # Write to disk immediately
                    exporter.write_record(seq_record)
                    _report("download", download_count, total_filtered)

            return exporter.get_output_files()

    # _export is no longer needed as StreamingExporter handles it.
