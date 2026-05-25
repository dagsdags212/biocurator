"""
Biocurator Status Command
=========================

This module implements the `biocurator status` command for probing
configured database providers and displaying health status.

© Jan Emmanuel Samson (2026-)
"""

from typing import Annotated
import typer
from rich.table import Table
from rich.console import Console
from biocurator.cli.main import (
    console,
    print_error,
    print_info,
    print_warning,
)
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
        print_error(str(exc))
        raise typer.Exit(1)
    except InvalidConfigError as exc:
        print_error(f"Invalid config: {exc}")
        raise typer.Exit(1)

    curator = Biocurator(
        email=global_config.email,
        global_retry=global_config.retry,
        global_breaker=global_config.breaker,
    )

    if not curator.searchers:
        print_warning("No database providers configured.")
        raise typer.Exit(0)

    print_info("Probing provider health...\n")

    statuses = curator.get_health_status()

    table = Table(
        title="Provider Health Status",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Provider", style="cyan")
    table.add_column("Status", no_wrap=True)
    table.add_column("Response Time", justify="right")
    table.add_column("Breaker State")

    for s in statuses:
        if s["status"] == "UP":
            status_display = "[bold green]UP[/bold green]"
        elif s["status"] == "DOWN":
            status_display = "[bold red]DOWN[/bold red]"
        else:
            status_display = "[bold yellow]UNKNOWN[/bold yellow]"

        bs = s["breaker_state"]
        if bs == "closed":
            breaker_display = "[bold green]closed[/bold green]"
        elif bs == "half_open":
            breaker_display = "[bold yellow]half_open[/bold yellow]"
        elif bs == "open":
            breaker_display = "[bold red]open[/bold red]"
        elif bs is None:
            breaker_display = "[dim]N/A[/dim]"
        else:
            breaker_display = bs

        rt = s["response_time_ms"]
        if rt > 0:
            rt_display = f"{rt:.0f}ms"
        else:
            rt_display = "[dim]N/A[/dim]"

        table.add_row(s["provider"], status_display, rt_display, breaker_display)

    console.print(table)
    console.print()

    up_count = sum(1 for s in statuses if s["status"] == "UP")
    down_count = sum(1 for s in statuses if s["status"] == "DOWN")
    console.print(
        f"[dim]{up_count} reachable, {down_count} unreachable, "
        f"{len(statuses)} total providers[/dim]"
    )
