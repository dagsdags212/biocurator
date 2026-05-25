"""
Verification Module
===================

Provides library functions for verifying manifest checksums against
files on disk. Phase 4 CLI wraps these with Typer.


© Jan Emmanuel Samson (2026-)
"""

import hashlib
import json
from pathlib import Path
from typing import Any

from biocurator.utils.logging import get_logger

logger = get_logger(__name__)


def manifest_verify(manifest_path: Path) -> dict[str, Any]:
    """Verify checksums in manifest against files on disk.

    Parameters
    ----------
    manifest_path : Path
        Path to the manifest.json file.

    Returns
    -------
    dict[str, Any]
        Verification report with keys:

        - manifest_path: str
        - manifest_valid: bool
        - files_checked: int
        - files_matched: int
        - files_missing: int
        - files_corrupted: int
        - results: list[dict] with per-file {path, sha256_expected, sha256_actual, status}
    """
    manifest_path = Path(manifest_path)

    # Load manifest JSON
    try:
        manifest = json.loads(manifest_path.read_text())
        manifest_valid = True
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning(f"Cannot parse manifest: {exc}")
        return {
            "manifest_path": str(manifest_path),
            "manifest_valid": False,
            "files_checked": 0,
            "files_matched": 0,
            "files_missing": 0,
            "files_corrupted": 0,
            "results": [],
        }

    base_dir = manifest_path.parent
    results = []
    files_matched = 0
    files_missing = 0
    files_corrupted = 0

    for file_entry in manifest.get("files", []):
        rel_path = file_entry.get("path", "")
        expected_sha256 = file_entry.get("sha256", "")

        # Security: reject traversal paths per RESEARCH.md V5 mitigation
        if ".." in rel_path or rel_path.startswith("/"):
            logger.warning(f"Skipping suspicious path in manifest: {rel_path}")
            continue

        # Resolve path relative to manifest directory (D-03: portable)
        file_path = base_dir / rel_path

        if not file_path.exists():
            results.append({
                "path": rel_path,
                "sha256_expected": expected_sha256,
                "sha256_actual": None,
                "status": "missing",
            })
            files_missing += 1
            continue

        # Re-compute SHA-256 from disk (anti-pattern avoidance: never trust stored checksum)
        h = hashlib.sha256()
        with open(file_path, "rb") as fh:
            for chunk in iter(lambda: fh.read(8192), b""):
                h.update(chunk)
        actual = h.hexdigest()

        if actual == expected_sha256:
            status = "ok"
            files_matched += 1
        else:
            status = "corrupted"
            files_corrupted += 1

        results.append({
            "path": rel_path,
            "sha256_expected": expected_sha256,
            "sha256_actual": actual,
            "status": status,
        })

    return {
        "manifest_path": str(manifest_path),
        "manifest_valid": manifest_valid,
        "files_checked": len(results),
        "files_matched": files_matched,
        "files_missing": files_missing,
        "files_corrupted": files_corrupted,
        "results": results,
    }
