"""
Biocurator CLI
==============

This contains the code for running the Biocurator CLI


© Jan Emmanuel Samson (2026-)
"""

from typing import Annotated, Optional, List
from enum import Enum
import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from biocurator.utils.logging import get_logger


console = Console()
logger = get_logger(__name__)


class SequenceType(str, Enum):
    """Supported sequence types"""

    nucleotide = "nucleotide"
    protein = "protein"
    sra = "sra"


class DatabaseType(str, Enum):
    """Supported database types"""

    ncbi = "ncbi"
    uniprot = "uniprot"


from biocurator.cli.commands.init import init_command

app = typer.Typer(
    name="biocurator",
    help="🧬 Biocurator: a biological dataset curation framework",
    add_completion=True,
    rich_markup_mode="rich",
    no_args_is_help=True,
)

app.command("init")(init_command)


# Utility functions for rich output
def print_success(message: str):
    """Print success message with green checkmark."""
    rprint(f"[bold green]✅ {message}[/bold green]")


def print_error(message: str):
    """Print error message with red X."""
    rprint(f"[bold red]❌ {message}[/bold red]")


def print_warning(message: str):
    """Print warning message with yellow triangle."""
    rprint(f"[bold yellow]⚠️  {message}[/bold yellow]")


def print_info(message: str):
    """Print info message with blue info icon."""
    rprint(f"[bold blue]ℹ️  {message}[/bold blue]")


def print_header(title: str):
    """Print header with panel."""
    console.print(Panel.fit(f"[bold cyan]{title}[/bold cyan]", border_style="cyan"))


@app.callback()
def main(
    debug: Annotated[
        bool, typer.Option("--debug", help="Enable debug logging")
    ] = False,
    version: Annotated[
        bool, typer.Option("--version", help="Show version and exit")
    ] = False,
):
    """
    🧬 BioCurator: Comprehensive biological dataset curation framework.

    A powerful tool for searching, downloading, and analyzing biological sequences
    from multiple databases including NCBI and UniProt.

    """
    if version:
        from biocurator import __version__

        rprint(f"BioCurator version [bold green]{__version__}[/bold green]")
        raise typer.Exit()

    if debug:
        setup_development_logging()
        print_info("Debug logging enabled")
