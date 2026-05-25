"""
Biocurator Files Command — list downloaded files and optionally verify checksums.
"""

import json
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.table import Table

from biocurator.cli.main import console
from biocurator.config.loader import ConfigLoader
from biocurator.core import manifest_verify
from biocurator.exceptions import ConfigNotFoundError, InvalidConfigError


def _format_size(size_bytes: int) -> str:
    if size_bytes >= 1_048_576:
        return f"{size_bytes / 1_048_576:.1f} MB"
    if size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes} B"


def files_command(
    job_name: Annotated[
        Optional[str],
        typer.Argument(help="Job name to inspect (omit for summary of all jobs)"),
    ] = None,
    config: Annotated[
        str,
        typer.Option("--config", "-c", help="Path to the YAML config file"),
    ] = "biocurator_config.yaml",
    verify: Annotated[
        bool,
        typer.Option("--verify", help="Re-read files and verify SHA-256 checksums"),
    ] = False,
) -> None:
    """List downloaded files for a job, or summarize all jobs with data. Use --verify to re-check checksums."""
    try:
        global_config = ConfigLoader.load(config)
    except ConfigNotFoundError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(1)
    except InvalidConfigError as exc:
        console.print(f"[bold red]Invalid config:[/bold red] {exc}")
        raise typer.Exit(1)

    if verify:
        _handle_verify(job_name, global_config, config)
        return

    if job_name is not None:
        _handle_single_job_list(job_name, global_config)
    else:
        _handle_all_jobs_summary(global_config)


def _find_job(job_name: str, global_config):
    """Return the matching JobConfig or None."""
    for job in global_config.jobs:
        if job.name == job_name:
            return job
    return None


def _handle_single_job_list(job_name: str, global_config) -> None:
    """Display file list for a single named job."""
    job = _find_job(job_name, global_config)
    if job is None:
        available = ", ".join(j.name for j in global_config.jobs)
        console.print(
            f"[bold red]Unknown job:[/bold red] {job_name}. Available: {available}"
        )
        raise typer.Exit(1)

    manifest_path = Path(job.export.outdir) / "manifest.json"
    if not manifest_path.exists():
        console.print(
            f"[yellow]No data for job '{job_name}' — run it with `biocurator run` first.[/yellow]"
        )
        return

    try:
        manifest = json.loads(manifest_path.read_text())
    except (json.JSONDecodeError, OSError):
        console.print(f"[bold red]Cannot read manifest:[/bold red] {manifest_path}")
        raise typer.Exit(1)

    table = Table(
        title=f"Files — {job_name}",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Filename", style="cyan")
    table.add_column("Format")
    table.add_column("Size", justify="right")
    table.add_column("Records", justify="right")
    table.add_column("SHA-256")

    for entry in manifest.get("files", []):
        table.add_row(
            entry["path"],
            entry["format"],
            _format_size(entry.get("size", 0)),
            str(entry.get("record_count", "—")),
            entry["sha256"][:12] + "...",
        )

    console.print(table)
    console.print(
        f"[dim]{manifest['stats']['total_files']} file(s), "
        f"{manifest['stats']['total_records']} record(s) — "
        f"generated {manifest['generated_at']}[/dim]"
    )


def _handle_all_jobs_summary(global_config) -> None:
    """Show a summary row for every job, indicating which have manifests."""
    table = Table(
        title="Downloaded Data",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Job", style="cyan")
    table.add_column("Output Dir")
    table.add_column("Files", justify="right")
    table.add_column("Records", justify="right")
    table.add_column("Manifest")

    jobs_with_data = 0
    for job in global_config.jobs:
        manifest_path = Path(job.export.outdir) / "manifest.json"
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text())
                table.add_row(
                    job.name,
                    job.export.outdir,
                    str(manifest["stats"]["total_files"]),
                    str(manifest["stats"]["total_records"]),
                    "[bold green]✓[/bold green]",
                )
                jobs_with_data += 1
            except (json.JSONDecodeError, OSError):
                table.add_row(
                    job.name,
                    job.export.outdir,
                    "[dim]—[/dim]",
                    "[dim]—[/dim]",
                    "[bold red]corrupt[/bold red]",
                )
        else:
            table.add_row(
                job.name,
                job.export.outdir,
                "[dim]—[/dim]",
                "[dim]—[/dim]",
                "[dim]none[/dim]",
            )

    console.print(table)
    if jobs_with_data == 0:
        console.print(
            "[yellow]No downloaded data found. Run jobs with `biocurator run` first.[/yellow]"
        )


def _handle_verify(job_name: Optional[str], global_config, config: str) -> None:
    """Re-read files from disk, verify SHA-256 checksums, report per-file status."""
    if job_name is not None:
        # Single-job verify
        job = _find_job(job_name, global_config)
        if job is None:
            available = ", ".join(j.name for j in global_config.jobs)
            console.print(
                f"[bold red]Unknown job:[/bold red] {job_name}. Available: {available}"
            )
            raise typer.Exit(1)
        failed = _verify_one_job(job_name, Path(job.export.outdir))
        if failed:
            raise typer.Exit(1)
    else:
        # All-jobs verify
        jobs_with_manifests = [
            j
            for j in global_config.jobs
            if (Path(j.export.outdir) / "manifest.json").exists()
        ]
        if not jobs_with_manifests:
            console.print(
                "[yellow]No manifests found — run jobs first.[/yellow]"
            )
            return

        any_failure = False
        for job in jobs_with_manifests:
            failed = _verify_one_job(job.name, Path(job.export.outdir))
            if failed:
                any_failure = True

        if any_failure:
            raise typer.Exit(1)


def _verify_one_job(job_name: str, outdir: Path) -> bool:
    """Run manifest_verify for one job and render results. Returns True if any failure."""
    manifest_path = outdir / "manifest.json"
    if not manifest_path.exists():
        console.print(
            f"[yellow]No manifest for '{job_name}' — run the job first.[/yellow]"
        )
        return False

    result = manifest_verify(manifest_path)

    if not result["manifest_valid"]:
        console.print(
            f"[bold red]Cannot parse manifest:[/bold red] {manifest_path}"
        )
        raise typer.Exit(1)

    table = Table(
        title=f"Verification — {job_name}",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Filename", style="cyan")
    table.add_column("Status")
    table.add_column("SHA-256 Match")
    table.add_column("Notes")

    for entry in result["results"]:
        status = entry["status"]
        if status == "ok":
            status_display = "[bold green]✓ ok[/bold green]"
            match_display = "[bold green]✓[/bold green]"
            notes = ""
        elif status == "corrupted":
            status_display = "[bold red]✗ corrupted[/bold red]"
            match_display = "[bold red]✗[/bold red]"
            notes = f"expected: {entry['sha256_expected'][:12]}..."
        else:  # missing
            status_display = "[bold yellow]? missing[/bold yellow]"
            match_display = "[dim]N/A[/dim]"
            notes = "File not found on disk"

        table.add_row(entry["path"], status_display, match_display, notes)

    console.print(table)

    if result["all_ok"]:
        console.print("[bold green]All checksums verified ✓[/bold green]")
        return False
    else:
        console.print(
            f"[bold red]Issues found: {result['files_corrupted']} corrupted, "
            f"{result['files_missing']} missing[/bold red]"
        )
        return True
