"""
Biocurator CLI
==============

This contains the code for running the Biocurator CLI


© Jan Emmanuel Samson (2026-)
"""

from typing import Annotated
import typer
from rich import print as rprint
from rich.console import Console
from biocurator.utils.logging import get_logger, enable_verbose_logging


console = Console()
logger = get_logger(__name__)


from biocurator.cli.commands.init import init_command
from biocurator.cli.commands.run import run_command
from biocurator.cli.commands.preview import preview_command
from biocurator.cli.commands.status import status_command


def _version_callback(value: bool) -> None:
    if value:
        from biocurator import __version__

        rprint(f"Biocurator [bold green]{__version__}[/bold green]")
        raise typer.Exit()


app = typer.Typer(
    name="biocurator",
    help="🧬 Biocurator: a biological dataset curation framework",
    add_completion=True,
    rich_markup_mode="rich",
    no_args_is_help=True,
)

app.command("init")(init_command)
app.command("run")(run_command)
app.command("preview")(preview_command)
app.command("status")(status_command)


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


@app.callback()
def main(
    debug: Annotated[
        bool, typer.Option("--debug", help="Print log messages to stdout")
    ] = False,
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            help="Show version and exit",
            callback=_version_callback,
            is_eager=True,
        ),
    ] = False,
):
    """
    🧬 BioCurator: Comprehensive biological dataset curation framework.

    A powerful tool for searching, downloading, and analyzing biological sequences
    from multiple databases including NCBI and UniProt.

    """
    if debug:
        enable_verbose_logging()
        print_info("Debug logging enabled")
