from typing import Annotated, Optional
import typer
from biocurator.cli.main import console
from rich.table import Table
from biocurator.config.loader import ConfigLoader
from biocurator.core.curator import Biocurator
from biocurator.exceptions import ConfigNotFoundError, InvalidConfigError
from biocurator.providers import (
    NCBISearchCriteria,
    UniProtSearchCriteria,
    SearchCriteria,
)


def preview_command(
    job_name: Annotated[str, typer.Argument(help="Name of the job to preview")],
    config: Annotated[
        str, typer.Option("--config", "-c", help="Path to the YAML config file")
    ] = "config.yaml",
):
    """Preview search results for a specific job without downloading sequences."""
    try:
        global_config = ConfigLoader.load(config)
    except ConfigNotFoundError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(1)
    except InvalidConfigError as exc:
        console.print(f"[bold red]Invalid config:[/bold red] {exc}")
        raise typer.Exit(1)

    name_map = {j.name: j for j in global_config.jobs}
    if job_name not in name_map:
        console.print(f"[bold red]Unknown job:[/bold red] {job_name}")
        raise typer.Exit(1)

    job = name_map[job_name]
    curator = Biocurator(
        email=global_config.email,
        global_retry=global_config.retry,
        global_breaker=global_config.breaker,
    )

    console.print(
        f"[bold cyan]Previewing results for job:[/bold cyan] [bold]{job_name}[/bold]"
    )

    for db_name in job.search.databases:
        if db_name not in curator.searchers:
            console.print(
                f"[yellow]Database '{db_name}' not configured, skipping[/yellow]"
            )
            continue

        searcher = curator.searchers[db_name]
        search_cfg = job.search
        filter_cfg = job.filter

        common_kwargs = dict(
            organism=search_cfg.organism,
            keywords=search_cfg.keywords,
            min_length=filter_cfg.min_length,
            max_length=filter_cfg.max_length,
            # For preview, we don't want too many results
            max_results=min(search_cfg.max_results, 10),
            exclude_terms=filter_cfg.exclude_terms,
            start_date=search_cfg.date_range.get("start")
            if search_cfg.date_range
            else None,
            end_date=search_cfg.date_range.get("end")
            if search_cfg.date_range
            else None,
        )

        if db_name == "ncbi":
            from biocurator.providers.base import NCBIDatabase as _NCBIDb

            criteria = NCBISearchCriteria(database=_NCBIDb.NUCCORE, **common_kwargs)
        elif db_name == "uniprot":
            criteria = UniProtSearchCriteria(**common_kwargs)
        else:
            criteria = SearchCriteria(**common_kwargs)

        with console.status(f"[bold blue]Searching {db_name.upper()}..."):
            ids = searcher.search(criteria)
            if not ids:
                console.print(f"No results found in {db_name.upper()}.")
                continue

            metadata_iter = searcher.fetch_metadata(ids, criteria)

            table = Table(
                title=f"Results from {db_name.upper()}",
                show_header=True,
                header_style="bold magenta",
            )
            table.add_column("Accession", style="cyan")
            table.add_column("Title")
            table.add_column("Organism", style="green")
            table.add_column("Length", justify="right")

            count = 0
            for record in metadata_iter:
                table.add_row(
                    record.accession,
                    record.title[:50] + "..."
                    if len(record.title) > 50
                    else record.title,
                    record.organism,
                    str(record.sequence_length),
                )
                count += 1

            console.print(table)
            console.print(f"[dim]Showing {count} of {len(ids)} total matches[/dim]\n")
