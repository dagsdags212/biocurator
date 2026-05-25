from typing import Annotated, Optional, Dict
import typer
from biocurator.cli.main import console
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TimeElapsedColumn,
    MofNCompleteColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.text import Text
from rich.table import Table
from biocurator.config.loader import ConfigLoader
from biocurator.core.curator import Biocurator
from biocurator.exceptions import ConfigNotFoundError, InvalidConfigError
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
    check: Annotated[
        Optional[bool],
        typer.Option(
            "--check/--no-check",
            help="Run pre-flight health check before executing jobs. "
            "Overrides the per-job search.preflight_check config setting.",
        ),
    ] = None,
):
    """Run curation jobs defined in a YAML config file.

    Use --check to probe provider health before executing jobs.
    Use --no-check to skip pre-flight checks even if configured in the config file.
    """
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

    curator = Biocurator(email=global_config.email, global_retry=global_config.retry)

    summary_rows = []

    # Custom Progress that shows speed as "items/s"
    class ProcessingSpeedColumn(TransferSpeedColumn):
        def render(self, task) -> Text:
            speed = task.finished_speed or task.speed
            if speed is None:
                return Text("-", style="progress.remaining")
            return Text(f"{speed:.1f} it/s", style="progress.data.speed")

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.fields[job_name]}", justify="right"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=None),
        MofNCompleteColumn(),
        TaskProgressColumn(),
        ProcessingSpeedColumn(),
        TimeRemainingColumn(),
        console=console,
        expand=True,
    ) as progress:
        # Initialize all tasks upfront
        task_ids: Dict[str, int] = {}
        for job in selected_jobs:
            task_id = progress.add_task(
                "pending", job_name=job.name, total=None, start=False
            )
            task_ids[job.name] = task_id

        for job in selected_jobs:
            task_id = task_ids[job.name]
            progress.start_task(task_id)
            progress.update(task_id, description="searching")

            def make_callback(t_id):
                def callback(phase, current, total):
                    progress.update(
                        t_id,
                        description=phase,
                        completed=current,
                        total=total,
                    )

                return callback

            try:
                output_files = curator.run_job(
                    job, progress_callback=make_callback(task_id)
                )
                progress.update(task_id, description="[green]done")
                summary_rows.append(
                    (job.name, "[green]done[/]", f"{len(output_files)} file(s)")
                )
            except Exception as exc:
                progress.update(task_id, description=f"[red]failed")
                summary_rows.append((job.name, f"[red]failed: {exc}[/]", "0"))

    table = Table(title="Run Summary", show_header=True, header_style="bold magenta")
    table.add_column("Job", style="bold")
    table.add_column("Status")
    table.add_column("Output")
    for row in summary_rows:
        table.add_row(*row)
    console.print(table)
