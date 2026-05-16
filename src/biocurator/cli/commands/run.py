from pathlib import Path
from typing import Annotated, Optional
import typer
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table
from biocurator.config.loader import ConfigLoader
from biocurator.core.curator import Biocurator
from biocurator.exceptions import (
    ConfigNotFoundError,
    InvalidConfigError,
    JobNotFoundError,
)
from biocurator.utils.logging import enable_verbose_logging


def run_command(
    config: Annotated[str, typer.Argument(help="Path to the YAML config file")],
    jobs: Annotated[
        Optional[str],
        typer.Option(
            "--jobs", "-j", help="Comma-separated job names to run (default: all)"
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run", help="Validate config and preview jobs without downloading"
        ),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose", "-v", help="Print timestamped log messages to stdout"
        ),
    ] = False,
):
    """Run curation jobs defined in a YAML config file."""
    console = Console()

    if verbose:
        enable_verbose_logging(console=console)

    try:
        global_config = ConfigLoader.load(config)
    except ConfigNotFoundError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(1)
    except InvalidConfigError as exc:
        console.print(f"[bold red]Invalid config:[/bold red] {exc}")
        raise typer.Exit(1)

    selected_jobs = global_config.jobs
    if jobs:
        job_names = [j.strip() for j in jobs.split(",")]
        name_map = {j.name: j for j in global_config.jobs}
        missing = [n for n in job_names if n not in name_map]
        if missing:
            console.print(f"[bold red]Unknown jobs:[/bold red] {', '.join(missing)}")
            raise typer.Exit(1)
        selected_jobs = [name_map[n] for n in job_names]

    if dry_run:
        console.print(
            f"[bold cyan]Dry run — {len(selected_jobs)} job(s) would execute:[/bold cyan]"
        )
        for job in selected_jobs:
            console.print(
                f"  • [bold]{job.name}[/bold]  databases={job.search.databases}"
            )
        return

    curator = Biocurator(email=global_config.email)

    summary_rows = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        for job in selected_jobs:
            task = progress.add_task(f"[{job.name}] search", total=4, completed=0)

            def make_callback(t):
                def callback(phase, current, total):
                    progress.update(t, description=f"[{job.name}] {phase}", advance=1)

                return callback

            output_files = curator.run_job(job, progress_callback=make_callback(task))
            summary_rows.append((job.name, "done", str(len(output_files)) + " file(s)"))

    table = Table(title="Run Summary")
    table.add_column("Job", style="bold")
    table.add_column("Status")
    table.add_column("Output")
    for row in summary_rows:
        table.add_row(*row)
    console.print(table)
