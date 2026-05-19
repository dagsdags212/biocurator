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

from biocurator.providers import ProviderRegistry, DatabaseConfig, SearchCriteria
from biocurator.providers.ncbi import NCBISearchCriteria
from biocurator.providers.uniprot import UniProtSearchCriteria
from .filters import SequenceFilter
from ..utils.logging import get_logger

# Get logger for this module
logger = get_logger(__name__)


class Biocurator:
    """Main Biocurator class for biological dataset curation."""

    def __init__(self, email: str, outdir: Optional[str] = None) -> None:
        """Initialize BioCurator.

        Parameters
        ----------
        email : str
            Email address for database access
        outdir : str, optional
            Output directory for results
        """
        logger.info("Initializing Biocurator")
        self.email = email
        self.outdir = Path(outdir) if outdir else Path("biocurator_output")
        self.searchers: dict = {}
        self.sequences: list = []
        self.metadata: list = []
        self._init_database_searchers()
        logger.info("Biocurator initialization complete")

    def _init_database_searchers(self) -> None:
        logger.info("Initializing database searchers")
        ncbi_cfg = DatabaseConfig(name="NCBI", rate_limit=0.3, batch_size=20)
        self.searchers["ncbi"] = ProviderRegistry.get("ncbi", ncbi_cfg, self.email)
        uniprot_cfg = DatabaseConfig(
            name="UniProt",
            base_url="https://rest.uniprot.org",
            rate_limit=0.5,
            batch_size=25,
        )
        self.searchers["uniprot"] = ProviderRegistry.get(
            "uniprot", uniprot_cfg, self.email
        )
        logger.info(f"Database searchers initialized: {list(self.searchers.keys())}")

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

        def _report(phase, current, total):
            if progress_callback:
                progress_callback(phase, current, total)

        all_sequences = []
        all_metadata = []

        for db_name in job_config.search.databases:
            if db_name not in self.searchers:
                logger.warning(f"Database '{db_name}' not configured, skipping")
                continue

            searcher = self.searchers[db_name]
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
            _report("search", len(ids), len(ids))

            if not ids:
                continue

            metadata = searcher.fetch_metadata(ids)
            filtered_metadata = SequenceFilter.filter_by_criteria(metadata, criteria)
            _report("filter", len(filtered_metadata), len(metadata))

            if not filtered_metadata:
                continue

            filtered_ids = [m.id for m in filtered_metadata]
            export_dir = Path(job_config.export.outdir)
            export_dir.mkdir(parents=True, exist_ok=True)
            sequences = searcher.download(filtered_ids, export_dir)

            if criteria.quality_threshold and sequences:
                sequences = SequenceFilter.apply_quality_filter(
                    sequences, criteria.quality_threshold
                )

            _report("download", len(sequences), len(filtered_ids))

            all_sequences.extend(sequences)
            all_metadata.extend(filtered_metadata)

        if not all_sequences:
            return {}

        self.sequences = all_sequences
        self.metadata = all_metadata

        output_files = self._export(job_config.export)
        _report("export", len(output_files), len(output_files))
        return output_files

    def _export(self, export_config) -> dict:
        """Write sequences and metadata to disk."""
        from biocurator.exceptions import ExportError

        export_dir = Path(export_config.outdir)
        export_dir.mkdir(parents=True, exist_ok=True)
        prefix = export_config.prefix
        output_files = {}

        try:
            if "fasta" in export_config.formats:
                fasta_file = export_dir / f"{prefix}_sequences.fasta"
                with open(fasta_file, "w") as f:
                    for seq in self.sequences:
                        f.write(f">{seq.accession} {seq.description}\n")
                        f.write(f"{seq.sequence}\n")
                output_files["fasta"] = fasta_file

            if "csv" in export_config.formats and self.metadata:
                csv_file = export_dir / f"{prefix}_metadata.csv"
                pd.DataFrame([vars(r) for r in self.metadata]).to_csv(csv_file, index=False)
                output_files["csv"] = csv_file

            if "json" in export_config.formats and self.metadata:
                import json as _json

                json_file = export_dir / f"{prefix}_metadata.json"
                with open(json_file, "w") as f:
                    _json.dump([vars(r) for r in self.metadata], f, indent=2, default=str)
                output_files["json"] = json_file

        except OSError as exc:
            raise ExportError(f"Failed to write output: {exc}") from exc

        return output_files

