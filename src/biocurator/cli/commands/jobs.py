"""
Biocurator Jobs Command — lists all curation jobs defined in a YAML config.
"""

from typing import Annotated

import typer
from rich.table import Table

from biocurator.cli.main import console
from biocurator.config.loader import ConfigLoader
from biocurator.exceptions import ConfigNotFoundError, InvalidConfigError


def jobs_command(
    config: Annotated[
        str,
        typer.Option("--config", "-c", help="Path to the YAML config file"),
    ] = "biocurator_config.yaml",
) -> None:
    """List all curation jobs defined in the YAML config file."""
    try:
        global_config = ConfigLoader.load(config)
    except ConfigNotFoundError as exc:
        console.print(
            f"[bold red]Error:[/bold red] {exc} — specify a config path with --config"
        )
        raise typer.Exit(1)
    except InvalidConfigError as exc:
        console.print(f"[bold red]Invalid config:[/bold red] {exc}")
        raise typer.Exit(1)

    table = Table(
        title="Curation Jobs",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Job Name", style="cyan")
    table.add_column("Databases")
    table.add_column("Organism")
    table.add_column("Max Results", justify="right")
    table.add_column("Output Dir")
    table.add_column("Formats")

    for job in global_config.jobs:
        table.add_row(
            job.name,
            ", ".join(job.search.databases),
            job.search.organism or "[dim]—[/dim]",
            str(job.search.max_results),
            job.export.outdir,
            ", ".join(job.export.formats),
        )

    console.print(table)
    console.print()
    console.print(f"[dim]{len(global_config.jobs)} job(s) defined in {config}[/dim]")
