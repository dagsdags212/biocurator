"""
Streaming Exporter Module
=========================

This module provides a StreamingExporter class for writing biological
sequences and metadata to disk incrementally.


© Jan Emmanuel Samson (2026-)
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional, TextIO
import pandas as pd
from biocurator.providers.base import SequenceRecord
from biocurator.utils.logging import get_logger

logger = get_logger(__name__)


class StreamingExporter:
    """Manages incremental writing of sequences and metadata to files."""

    def __init__(
        self,
        outdir: Path,
        prefix: str,
        formats: List[str],
    ) -> None:
        """Initialize the StreamingExporter.

        Parameters
        ----------
        outdir : Path
            Directory to write output files to.
        prefix : str
            Prefix for output filenames.
        formats : List[str]
            List of formats to export (fasta, csv, json).
        """
        self.outdir = outdir
        self.prefix = prefix
        self.formats = formats
        self.outdir.mkdir(parents=True, exist_ok=True)
        
        self.file_handles: Dict[str, TextIO] = {}
        self.output_paths: Dict[str, Path] = {}
        self.metadata_buffer: List[SequenceRecord] = []
        self._is_first_csv_row = True

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def open(self) -> None:
        """Open file handles for requested formats."""
        if "fasta" in self.formats:
            path = self.outdir / f"{self.prefix}_sequences.fasta"
            self.file_handles["fasta"] = open(path, "w")
            self.output_paths["fasta"] = path

        if "csv" in self.formats:
            path = self.outdir / f"{self.prefix}_metadata.csv"
            self.file_handles["csv"] = open(path, "w")
            self.output_paths["csv"] = path

        if "json" in self.formats:
            path = self.outdir / f"{self.prefix}_metadata.json"
            self.file_handles["json"] = open(path, "w")
            self.output_paths["json"] = path
            # Start JSON list
            self.file_handles["json"].write("[\n")

    def write_record(self, record: SequenceRecord) -> None:
        """Write a single record to all active file handles."""
        # FASTA
        if "fasta" in self.file_handles and record.sequence:
            f = self.file_handles["fasta"]
            desc = record.description if record.description else record.title
            f.write(f">{record.accession} {desc}\n")
            f.write(f"{record.sequence}\n")

        # CSV
        if "csv" in self.file_handles:
            f = self.file_handles["csv"]
            data = vars(record)
            df = pd.DataFrame([data])
            df.to_csv(f, header=self._is_first_csv_row, index=False, mode='a')
            self._is_first_csv_row = False

        # JSON
        if "json" in self.file_handles:
            f = self.file_handles["json"]
            if not hasattr(self, "_json_count"):
                self._json_count = 0
            
            if self._json_count > 0:
                f.write(",\n")
            
            json.dump(vars(record), f, indent=2, default=str)
            self._json_count += 1

    def close(self) -> None:
        """Close all open file handles."""
        if "json" in self.file_handles:
            # End JSON list
            self.file_handles["json"].write("\n]")

        for handle in self.file_handles.values():
            handle.close()
        
        self.file_handles.clear()
        logger.info(f"Streaming export to {self.outdir} complete.")

    def get_output_files(self) -> Dict[str, Path]:
        """Return a mapping of format names to output file Paths."""
        return self.output_paths
