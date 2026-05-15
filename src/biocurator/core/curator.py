"""
Biocurator Module
====================

This module contains the main Biocurator class that coordinates
sequence search, download, filtering, and organization.
"""

import json
import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

from .searchers import SearchCriteria, DatabaseConfig, NCBISearcher, UniProtSearcher
from .filters import SequenceFilter
from ..utils.logging import (
    get_logger,
    get_performance_logger,
    log_function_call,
    log_config,
)

# Get logger for this module
logger = get_logger(__name__)
perf_logger = get_performance_logger(__name__)


class BioCurator:
    """Main BioCurator class for biological dataset curation."""

    def __init__(
        self,
        config_file: Optional[str] = None,
        email: Optional[str] = None,
        outdir: Optional[str] = None,
    ):
        """Initialize BioCurator with configuration.

        Parameters
        ----------
        config_file : str, optional
            Path to configuration file (YAML or JSON)
        email : str, optional
            Email address for database access
        output_dir : str, optional
            Output directory for results
        """
        logger.info("Initializing Biocurator")

        self.config = self._load_config(config_file)

        # Override config with parameters if provided
        if email:
            self.config["email"] = email
            logger.debug(f"Email set to: {email}")

        if outdir:
            self.config["output_directory"] = outdir
            logger.debug(f"Output directory set to: {outdir}")

        self.outdir = Path(self.config.get("output_directory", "biocurator_output"))
        self.outdir.mkdir(exist_ok=True)
        logger.info(f"Output directory: {self.outdir}")

        # Initialize database searchers
        self.searchers = {}
        self._init_database_searchers()

        self.sequences = []
        self.metadata = []

        logger.info("Biocurator initialization complete")

    @log_function_call
    def _load_config(self, config_file: Optional[str]) -> Dict[str, Any]:
        """Load configuration from file.

        Parameters
        ----------
        config_file : str, optional
            Path to configuration file

        Returns
        -------
        Dict[str, Any]
            Configuration dictionary
        """
        if config_file and Path(config_file).exists():
            import yaml

            logger.info(f"Loading configuration from: {config_file}")

            with open(config_file, "r") as f:
                if config_file.endswith((".yaml", ".yml")):
                    config = yaml.safe_load(f)
                else:
                    config = json.load(f)

            logger.info("Configuration loaded successfully")
            log_config(config, "biocurator.config")
            return config
        else:
            if config_file:
                logger.warning(
                    f"Configuration file not found: {config_file}, using defaults"
                )
            else:
                logger.info("No configuration file provided, using defaults")

            # Return default configuration
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration.

        Returns
        -------
        Dict[str, Any]
            Default configuration dictionary
        """
        logger.debug("Creating default configuration")

        config = {
            "databases": {
                "ncbi": {
                    "name": "NCBI",
                    "base_url": "https://eutils.ncbi.nlm.nih.gov",
                    "rate_limit": 0.3,
                    "batch_size": 20,
                },
                "uniprot": {
                    "name": "UniProt",
                    "base_url": "https://rest.uniprot.org",
                    "rate_limit": 0.5,
                    "batch_size": 25,
                },
            },
            "output_directory": "biocurator_output",
            "output_formats": ["fasta", "csv", "json"],
            "analysis": {
                "enable_statistics": True,
                "enable_visualization": True,
                "enable_conservation": True,
            },
        }

        logger.debug("Default configuration created")
        return config

    def _init_database_searchers(self):
        """Initialize database searchers."""
        logger.info("Initializing database searchers")

        email = self.config.get("email")
        if not email:
            error_msg = "Email address is required for database access"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Initialize NCBI searcher
        if "ncbi" in self.config["databases"]:
            try:
                ncbi_config = DatabaseConfig(**self.config["databases"]["ncbi"])
                self.searchers["ncbi"] = NCBISearcher(ncbi_config, email)
                logger.info("NCBI searcher initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize NCBI searcher: {e}")
                raise

        # Initialize UniProt searcher
        if "uniprot" in self.config["databases"]:
            try:
                uniprot_config = DatabaseConfig(**self.config["databases"]["uniprot"])
                self.searchers["uniprot"] = UniProtSearcher(uniprot_config, email)
                logger.info("UniProt searcher initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize UniProt searcher: {e}")
                raise

        logger.info(f"Database searchers initialized: {list(self.searchers.keys())}")

    def search_and_download(
        self, criteria: SearchCriteria, databases: Optional[List[str]] = None
    ) -> None:
        """Search databases and download sequences.

        Parameters
        ----------
        criteria : SearchCriteria
            Search criteria specification
        databases : List[str], optional
            List of databases to search. If None, uses all configured databases
        """
        perf_logger.start_timer("search_and_download")

        if databases is None:
            databases = list(self.searchers.keys())

        logger.info(f"Starting search and download for databases: {databases}")
        logger.info(
            f"Search criteria: organism='{criteria.organism}', "
            f"type='{criteria.sequence_type}', max_results={criteria.max_results}"
        )

        all_sequences = []
        all_metadata = []

        for db_name in databases:
            if db_name not in self.searchers:
                logger.warning(f"Database {db_name} not supported, skipping")
                continue

            searcher = self.searchers[db_name]
            logger.info(f"Processing database: {db_name.upper()}")

            try:
                # Search
                perf_logger.start_timer(f"search_{db_name}")
                ids = searcher.search(criteria)
                perf_logger.end_timer(f"search_{db_name}", sequence_count=len(ids))

                if not ids:
                    logger.warning(f"No sequences found in {db_name}")
                    continue

                # Fetch metadata
                perf_logger.start_timer(f"metadata_{db_name}")
                metadata = searcher.fetch_metadata(ids)
                perf_logger.end_timer(
                    f"metadata_{db_name}", metadata_count=len(metadata)
                )

                if not metadata:
                    logger.warning(f"No metadata retrieved from {db_name}")
                    continue

                # Filter sequences
                perf_logger.start_timer(f"filter_{db_name}")
                filtered_metadata = SequenceFilter.filter_by_criteria(
                    metadata, criteria
                )
                perf_logger.end_timer(
                    f"filter_{db_name}",
                    original_count=len(metadata),
                    filtered_count=len(filtered_metadata),
                )

                if not filtered_metadata:
                    logger.warning(f"No sequences passed filters for {db_name}")
                    continue

                # Download sequences
                perf_logger.start_timer(f"download_{db_name}")
                filtered_ids = [m["id"] for m in filtered_metadata]
                sequences = searcher.download_sequences(filtered_ids, self.output_dir)
                perf_logger.end_timer(
                    f"download_{db_name}", download_count=len(sequences)
                )

                all_sequences.extend(sequences)
                all_metadata.extend(filtered_metadata)

                logger.info(
                    f"Database {db_name} completed: {len(sequences)} sequences downloaded"
                )

            except Exception as e:
                logger.error(f"Error processing database {db_name}: {e}")
                continue

        # Remove duplicates if requested
        if len(all_sequences) > 1:
            original_count = len(all_sequences)
            all_sequences = SequenceFilter.remove_duplicates(
                all_sequences, by="accession"
            )
            # Update metadata to match deduplicated sequences
            seq_accessions = {seq["accession"] for seq in all_sequences}
            all_metadata = [
                m for m in all_metadata if m.get("accession") in seq_accessions
            ]

            if len(all_sequences) != original_count:
                logger.info(
                    f"Removed {original_count - len(all_sequences)} duplicate sequences"
                )

        self.sequences = all_sequences
        self.metadata = all_metadata

        perf_logger.end_timer(
            "search_and_download", total_sequences=len(self.sequences)
        )
        logger.info(
            f"Search and download completed: {len(self.sequences)} total sequences"
        )

    @log_function_call
    def save_results(self, prefix: str = "biocurator") -> Dict[str, Path]:
        """Save results in various formats.

        Parameters
        ----------
        prefix : str
            Prefix for output filenames

        Returns
        -------
        Dict[str, Path]
            Dictionary mapping format names to file paths
        """
        perf_logger.start_timer("save_results")
        logger.info("Saving results")

        if not self.sequences:
            logger.warning("No sequences to save")
            return {}

        output_files = {}

        try:
            # Save FASTA
            fasta_file = self.outdir / f"{prefix}_sequences.fasta"
            with open(fasta_file, "w") as f:
                for seq in self.sequences:
                    header = f">{seq['accession']} {seq.get('description', '')}"
                    f.write(f"{header}\n{seq['sequence']}\n")
            output_files["fasta"] = fasta_file
            logger.info(f"FASTA saved: {fasta_file} ({len(self.sequences)} sequences)")

            # Save metadata
            if self.metadata:
                # CSV format
                metadata_df = pd.DataFrame(self.metadata)
                csv_file = self.outdir / f"{prefix}_metadata.csv"
                metadata_df.to_csv(csv_file, index=False)
                output_files["csv"] = csv_file
                logger.info(f"Metadata CSV saved: {csv_file}")

                # JSON format
                json_file = self.outdir / f"{prefix}_metadata.json"
                with open(json_file, "w") as f:
                    json.dump(self.metadata, f, indent=2, default=str)
                output_files["json"] = json_file
                logger.info(f"Metadata JSON saved: {json_file}")

            # Generate summary
            summary_file = self.outdir / f"{prefix}_summary.txt"
            self._generate_summary_report(summary_file)
            output_files["summary"] = summary_file

            perf_logger.end_timer("save_results", files_created=len(output_files))
            logger.info(
                f"Results saved successfully: {len(output_files)} files created"
            )

        except Exception as e:
            logger.error(f"Error saving results: {e}")
            raise

        return output_files

    def _generate_summary_report(self, summary_file: Path):
        """Generate summary report.

        Parameters
        ----------
        summary_file : Path
            Path to summary file
        """
        logger.debug(f"Generating summary report: {summary_file}")

        try:
            with open(summary_file, "w") as f:
                f.write("BioCurator Dataset Summary\n")
                f.write("=" * 30 + "\n\n")
                f.write(f"Total sequences: {len(self.sequences)}\n")
                f.write(f"Extraction date: {datetime.now().isoformat()}\n\n")

                if self.sequences:
                    lengths = [s["sequence_length"] for s in self.sequences]
                    f.write("Sequence statistics:\n")
                    f.write(f"  Average length: {np.mean(lengths):.0f}\n")
                    f.write(f"  Median length: {np.median(lengths):.0f}\n")
                    f.write(f"  Length range: {min(lengths)} - {max(lengths)}\n")

                    # Database breakdown
                    databases = {}
                    for seq in self.metadata:
                        db = seq.get("database", "Unknown")
                        databases[db] = databases.get(db, 0) + 1

                    f.write("\nDatabase sources:\n")
                    for db, count in databases.items():
                        f.write(f"  {db}: {count} sequences\n")

                    # Organism breakdown (top 10)
                    organisms = {}
                    for seq in self.metadata:
                        org = seq.get("organism", "Unknown")
                        organisms[org] = organisms.get(org, 0) + 1

                    f.write("\nTop organisms:\n")
                    sorted_organisms = sorted(
                        organisms.items(), key=lambda x: x[1], reverse=True
                    )
                    for org, count in sorted_organisms[:10]:
                        f.write(f"  {org}: {count} sequences\n")

            logger.info(f"Summary report generated: {summary_file}")

        except Exception as e:
            logger.error(f"Error generating summary report: {e}")
            raise

    def get_statistics(self) -> Dict[str, Any]:
        """Get basic statistics about downloaded sequences.

        Returns
        -------
        Dict[str, Any]
            Statistics dictionary
        """
        logger.debug("Calculating statistics")

        if not self.sequences:
            return {"total_sequences": 0}

        lengths = [s["sequence_length"] for s in self.sequences]

        stats = {
            "total_sequences": len(self.sequences),
            "length_stats": {
                "mean": np.mean(lengths),
                "median": np.median(lengths),
                "std": np.std(lengths),
                "min": min(lengths),
                "max": max(lengths),
            },
        }

        # Database breakdown
        databases = {}
        for seq in self.metadata:
            db = seq.get("database", "Unknown")
            databases[db] = databases.get(db, 0) + 1
        stats["databases"] = databases

        # Organism breakdown
        organisms = {}
        for seq in self.metadata:
            org = seq.get("organism", "Unknown")
            organisms[org] = organisms.get(org, 0) + 1
        stats["top_organisms"] = dict(
            sorted(organisms.items(), key=lambda x: x[1], reverse=True)[:10]
        )

        logger.debug(f"Statistics calculated: {stats['total_sequences']} sequences")
        return stats

    @log_function_call
    def export_to_fasta(self, filename: Optional[Union[str, Path]] = None) -> Path:
        """Export sequences to FASTA format.

        Parameters
        ----------
        filename : str or Path, optional
            Output filename. If None, uses default naming

        Returns
        -------
        Path
            Path to created FASTA file
        """
        if filename is None:
            filename = self.outdir / "sequences.fasta"
        else:
            filename = Path(filename)

        logger.info(f"Exporting {len(self.sequences)} sequences to FASTA: {filename}")

        try:
            with open(filename, "w") as f:
                for seq in self.sequences:
                    header = f">{seq['accession']} {seq.get('description', '')}"
                    f.write(f"{header}\n{seq['sequence']}\n")

            logger.info(f"FASTA export completed: {filename}")

        except Exception as e:
            logger.error(f"Error exporting FASTA: {e}")
            raise

        return filename

    @log_function_call
    def load_results(self, input_dir: Union[str, Path]) -> bool:
        """Load previously saved results.

        Parameters
        ----------
        input_dir : str or Path
            Directory containing saved results

        Returns
        -------
        bool
            True if results were loaded successfully
        """
        input_dir = Path(input_dir)
        logger.info(f"Loading results from: {input_dir}")

        # Load sequences from FASTA
        fasta_files = list(input_dir.glob("*_sequences.fasta"))
        if not fasta_files:
            logger.error(f"No FASTA files found in {input_dir}")
            return False

        from Bio import SeqIO

        sequences = []
        fasta_file = fasta_files[0]
        logger.info(f"Loading sequences from: {fasta_file}")

        try:
            for record in SeqIO.parse(fasta_file, "fasta"):
                sequences.append(
                    {
                        "accession": record.id,
                        "description": record.description,
                        "sequence": str(record.seq),
                        "sequence_length": len(record.seq),
                    }
                )

            # Load metadata
            json_files = list(input_dir.glob("*_metadata.json"))
            metadata = []
            if json_files:
                json_file = json_files[0]
                logger.info(f"Loading metadata from: {json_file}")
                with open(json_file, "r") as f:
                    metadata = json.load(f)

            self.sequences = sequences
            self.metadata = metadata

            logger.info(
                f"Results loaded successfully: {len(sequences)} sequences, "
                f"{len(metadata)} metadata entries"
            )
            return True

        except Exception as e:
            logger.error(f"Error loading results: {e}")
            return False
