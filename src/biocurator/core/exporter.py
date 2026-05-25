"""
Streaming Exporter Module
=========================

This module provides a StreamingExporter class for writing biological
sequences and metadata to disk incrementally, with SHA-256 checksum
computation and per-job manifest generation.


© Jan Emmanuel Samson (2026-)
"""

import hashlib
import io
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, TextIO
import pandas as pd
from biocurator.config.schema import JobConfig
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
        job_name: str | None = None,
        databases: list[str] | None = None,
        job_config: JobConfig | None = None,
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
        job_name : str, optional
            Name of the curation job, used for manifest generation.
        databases : list[str], optional
            List of database provider names queried, used for manifest.
        job_config : JobConfig, optional
            Typed config for this job, embedded in manifest for provenance.
        """
        self.outdir = outdir
        self.prefix = prefix
        self.formats = formats
        self.outdir.mkdir(parents=True, exist_ok=True)

        self.file_handles: Dict[str, TextIO] = {}
        self.output_paths: Dict[str, Path] = {}
        self.metadata_buffer: List[SequenceRecord] = []
        self._is_first_csv_row = True
        self._hashers: dict[str, "hashlib._Hash"] = {}
        self._record_counts: dict[str, int] = {}
        self._checksums: dict[str, str] = {}
        self._job_name: str | None = job_name
        self._databases: list[str] = databases if databases is not None else []
        self._job_config: JobConfig | None = job_config

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # CR-02: only write manifest on clean exit; on exception the output
        # files may be truncated, so manifesting them would certify corrupt data.
        if exc_type is not None:
            for handle in self.file_handles.values():
                handle.close()
            self.file_handles.clear()
            logger.warning("Export aborted due to exception; manifest not written.")
        else:
            self.close()

    def open(self) -> None:
        """Open file handles for requested formats."""
        # CR-01: reset per-run state so a re-used instance starts clean.
        self._hashers = {}
        self._record_counts = {}
        self._checksums = {}
        self._is_first_csv_row = True
        self._json_count = 0

        if "fasta" in self.formats:
            path = self.outdir / f"{self.prefix}_sequences.fasta"
            # CR-05: explicit encoding so incremental hash (utf-8) matches on-disk bytes.
            self.file_handles["fasta"] = open(path, "w", encoding="utf-8", newline="\n")
            self.output_paths["fasta"] = path
            self._hashers["fasta"] = hashlib.sha256()
            self._record_counts["fasta"] = 0

        if "csv" in self.formats:
            path = self.outdir / f"{self.prefix}_metadata.csv"
            self.file_handles["csv"] = open(path, "w", encoding="utf-8", newline="\n")
            self.output_paths["csv"] = path
            self._hashers["csv"] = hashlib.sha256()
            self._record_counts["csv"] = 0

        if "json" in self.formats:
            path = self.outdir / f"{self.prefix}_metadata.json"
            self.file_handles["json"] = open(path, "w", encoding="utf-8", newline="\n")
            self.output_paths["json"] = path
            self._hashers["json"] = hashlib.sha256()
            self._record_counts["json"] = 0
            # Start JSON list
            self.file_handles["json"].write("[\n")
            # Hash the opening bracket
            self._hashers["json"].update(b"[\n")

    def write_record(self, record: SequenceRecord) -> None:
        """Write a single record to all active file handles."""
        # FASTA
        if "fasta" in self.file_handles and record.sequence:
            f = self.file_handles["fasta"]
            desc = record.description if record.description else record.title
            f.write(f">{record.accession} {desc}\n")
            f.write(f"{record.sequence}\n")
            # Hash the exact bytes written
            self._hashers["fasta"].update(
                f">{record.accession} {desc}\n{record.sequence}\n".encode("utf-8")
            )
            self._record_counts["fasta"] += 1

        # CSV — pre-buffer to StringIO, hash bytes, then write same bytes
        if "csv" in self.file_handles:
            f = self.file_handles["csv"]
            data = vars(record)
            df = pd.DataFrame([data])
            buf = io.StringIO()
            df.to_csv(buf, header=self._is_first_csv_row, index=False)
            csv_str = buf.getvalue()
            self._hashers["csv"].update(csv_str.encode("utf-8"))
            f.write(csv_str)
            self._is_first_csv_row = False
            self._record_counts["csv"] += 1

        # JSON — hash every write including commas and record data
        if "json" in self.file_handles:
            f = self.file_handles["json"]
            if not hasattr(self, "_json_count"):
                self._json_count = 0

            if self._json_count > 0:
                f.write(",\n")
                # Hash the comma+newline separator
                self._hashers["json"].update(b",\n")

            json.dump(vars(record), f, indent=2, default=str)
            # Hash the record JSON bytes (re-serialize to capture exact output)
            record_bytes = json.dumps(vars(record), indent=2, default=str).encode(
                "utf-8"
            )
            self._hashers["json"].update(record_bytes)
            self._json_count += 1
            self._record_counts["json"] += 1

    def close(self) -> None:
        """Close all open file handles and write manifest."""
        if "json" in self.file_handles:
            # End JSON list
            closing = "\n]"
            self.file_handles["json"].write(closing)
            # Hash the closing bracket
            self._hashers["json"].update(closing.encode("utf-8"))

        # Compute final digests before closing file handles
        self._checksums = {fmt: h.hexdigest() for fmt, h in self._hashers.items()}

        for handle in self.file_handles.values():
            handle.close()

        self.file_handles.clear()

        # Write manifest if configured
        self._write_manifest()

        logger.info(f"Streaming export to {self.outdir} complete.")

    def get_output_files(self) -> Dict[str, Path]:
        """Return a mapping of format names to output file Paths."""
        return self.output_paths

    def _write_manifest(self) -> None:
        """Write manifest.json and manifest-sha256.txt to output directory."""
        if not self._job_name:
            return  # manifest only written for full job runs, not standalone export

        manifest = {
            "manifest_version": "1.0",
            "job_name": self._job_name,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "config": asdict(self._job_config) if self._job_config else {},
            "databases": list(self._databases),
            "stats": {
                "total_records": sum(self._record_counts.values()),
                "total_files": len(self._checksums),
            },
            "files": [
                {
                    "path": p.name,
                    "format": fmt,
                    "sha256": self._checksums[fmt],
                    "size": p.stat().st_size,
                    "record_count": self._record_counts[fmt],
                    "provider": list(self._databases),
                }
                for fmt, p in self.output_paths.items()
            ],
        }

        try:
            manifest_path = self.outdir / "manifest.json"
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
        except OSError as exc:
            logger.warning(
                f"Failed to write manifest: {exc}. Export data is still valid."
            )

        try:
            # BagIt-compatible companion file (sha256sum -c format)
            lines = []
            for entry in manifest["files"]:
                lines.append(f"{entry['sha256']}  {entry['path']}")
            sha256sum_path = self.outdir / "manifest-sha256.txt"
            sha256sum_path.write_text("\n".join(lines) + "\n")
        except OSError as exc:
            logger.warning(f"Failed to write sha256sum companion file: {exc}.")
