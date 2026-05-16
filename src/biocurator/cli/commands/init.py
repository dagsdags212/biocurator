from pathlib import Path
from typing import Annotated
import typer
from rich.console import Console
from rich.syntax import Syntax

BASIC_TEMPLATE = """\
email: your@email.com

jobs:
  my-job:
    search:
      databases: [ncbi]
      organism: "Your organism"
      sequence_type: nucleotide
      keywords: []
      max_results: 100
    filter:
      min_length: null
      max_length: null
    export:
      outdir: results
      formats: [fasta, csv]
      prefix: output
"""

ADVANCED_TEMPLATE = """\
email: your@email.com

jobs:
  my-job:
    search:
      databases: [ncbi]
      organism: "Your organism"
      sequence_type: nucleotide   # nucleotide | protein | sra
      keywords: []
      max_results: 100
      exclude_terms: []
      location: null
      taxonomy_filter: null
      date_range:
        start: "2020/01/01"
        end: "2024/12/31"
    filter:
      min_length: null
      max_length: null
      exclude_terms: []
      quality_threshold: null     # 0.0 - 1.0
    export:
      outdir: results
      formats: [fasta, csv, json]
      prefix: output
"""


def init_command(
    output: Annotated[
        str | None,
        typer.Option(
            "--output", "-o", help="Write config to this file instead of stdout"
        ),
    ] = None,
    template: Annotated[
        str,
        typer.Option("--template", "-t", help="Template to use: basic or advanced"),
    ] = "basic",
):
    """Generate a starter config file."""
    content = ADVANCED_TEMPLATE if template == "advanced" else BASIC_TEMPLATE

    if output:
        path = Path(output)
        path.write_text(content)
        console = Console()
        console.print(f"[bold green]Config written to {path}[/bold green]")
    else:
        console = Console()
        syntax = Syntax(content, "yaml", theme="monokai", line_numbers=False)
        console.print(syntax)
