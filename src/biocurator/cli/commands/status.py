"""
Biocurator Status Command
=========================

This module implements the `biocurator status` command for probing
configured database providers and displaying health status.

© Jan Emmanuel Samson (2026-)
"""

from typing import Annotated
import typer
from biocurator.cli.main import console
from biocurator.config.loader import ConfigLoader
from biocurator.core.curator import Biocurator
from biocurator.exceptions import ConfigNotFoundError, InvalidConfigError


def status_command(
    config: Annotated[
        str,
        typer.Option("--config", "-c", help="Path to the YAML config file"),
    ] = "config.yaml",
):
    """Probe configured database providers and report health status.

    Displays a Rich table with per-provider reachability, response time,
    and circuit breaker state.
    """
    try:
        global_config = ConfigLoader.load(config)
    except ConfigNotFoundError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(1)
    except InvalidConfigError as exc:
        console.print(f"[bold red]Invalid config:[/bold red] {exc}")
        raise typer.Exit(1)

    curator = Biocurator(
        email=global_config.email,
        global_retry=global_config.retry,
        global_breaker=global_config.breaker,
    )

    if not curator.searchers:
        console.print("[yellow]No database providers configured.[/yellow]")
        raise typer.Exit(0)

    console.print("[bold blue]Probing provider health...[/bold blue]\n")

    from biocurator.cli.main import render_health_table

    statuses = curator.get_health_status()

    table = render_health_table(statuses, "Provider Health Status")
    console.print(table)
    console.print()

    up_count = sum(1 for s in statuses if s["status"] == "UP")
    down_count = sum(1 for s in statuses if s["status"] == "DOWN")
    console.print(
        f"[dim]{up_count} reachable, {down_count} unreachable, "
        f"{len(statuses)} total providers[/dim]"
    )
