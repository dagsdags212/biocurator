# Phase 4 — Pattern Map

> Closest existing analogs for each file to be created or modified.

---

## Files to Create

### `src/biocurator/cli/commands/jobs.py`

**Role:** CLI command module — list all jobs from config

**Closest analog:** `src/biocurator/cli/commands/status.py`

**Relevant pattern excerpts:**

```python
# Exact import pattern to replicate
from typing import Annotated
import typer
from rich.table import Table
from biocurator.cli.main import console
from biocurator.config.loader import ConfigLoader
from biocurator.exceptions import ConfigNotFoundError, InvalidConfigError

def status_command(
    config: Annotated[
        str,
        typer.Option("--config", "-c", help="Path to the YAML config file"),
    ] = "config.yaml",       # <-- jobs_command uses "biocurator_config.yaml" instead
):
    try:
        global_config = ConfigLoader.load(config)
    except ConfigNotFoundError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(1)
    except InvalidConfigError as exc:
        console.print(f"[bold red]Invalid config:[/bold red] {exc}")
        raise typer.Exit(1)

    # Rich table construction
    table = Table(title="...", show_header=True, header_style="bold magenta")
    table.add_column("Provider", style="cyan")
    table.add_column("Status", no_wrap=True)
    console.print(table)
```

**Differences for `jobs_command`:**
- Default config: `"biocurator_config.yaml"` (not `"config.yaml"`)
- Iterates `global_config.jobs` (list of `JobConfig`)
- Columns: `Job Name`, `Databases`, `Organism`, `Max Results`, `Output Dir`, `Formats`
- No external service calls needed (pure config display)
- Footer: `f"[dim]{len(jobs)} job(s) defined in {config}[/dim]"`

---

### `src/biocurator/cli/commands/files.py`

**Role:** CLI command module — list downloaded files and optionally verify checksums

**Closest analogs:**
1. `src/biocurator/cli/commands/status.py` — Rich table rendering pattern
2. `src/biocurator/cli/commands/run.py` — `--jobs` optional argument pattern
3. `src/biocurator/core/verifier.py` — `manifest_verify()` call site

**Relevant pattern excerpts:**

```python
# Optional positional argument pattern (from run.py --jobs option adapted to Argument)
job_name: Annotated[
    Optional[str],
    typer.Argument(help="Job name to inspect (omit to show all jobs with data)"),
] = None

# Boolean flag pattern (from run.py --dry-run)
verify: Annotated[
    bool,
    typer.Option("--verify", help="Re-read files and verify SHA-256 checksums"),
] = False

# manifest_verify() usage (from verifier.py public API)
from biocurator.core import manifest_verify
result = manifest_verify(manifest_path)
# result keys: manifest_valid, files_checked, files_matched, files_missing,
#              files_corrupted, all_ok, results (list of dicts)

# Exit code 1 on failure
raise typer.Exit(1)
```

**Table styling for verify status (mirrors status.py breaker state pattern):**
```python
if entry["status"] == "ok":
    status_display = "[bold green]✓ ok[/bold green]"
elif entry["status"] == "corrupted":
    status_display = "[bold red]✗ corrupted[/bold red]"
elif entry["status"] == "missing":
    status_display = "[bold yellow]? missing[/bold yellow]"
```

---

### `tests/cli/test_jobs.py`

**Closest analog:** `tests/cli/test_run.py`

**Exact pattern to replicate:**

```python
from typer.testing import CliRunner
from biocurator.cli.main import app

runner = CliRunner()

VALID_CONFIG = """\
email: test@example.com
jobs:
  test-job:
    search:
      databases: [ncbi]
      organism: "E. coli"
      max_results: 5
    filter: {}
    export:
      outdir: {outdir}
      formats: [fasta]
      prefix: test
"""

def test_something(tmp_path):
    cfg = tmp_path / "biocurator_config.yaml"
    cfg.write_text(VALID_CONFIG.format(outdir=str(tmp_path / "results")))
    result = runner.invoke(app, ["jobs", "--config", str(cfg)])
    assert result.exit_code == 0
```

**Key differences:**
- Config filename: `biocurator_config.yaml` (not `config.yaml`)
- No `patch()` needed — jobs command is pure config display, no external calls
- Test for default config discovery: invoke without `--config` in `tmp_path` as CWD (use `runner.invoke` with `env={"PWD": str(tmp_path)}` or write to CWD)

---

### `tests/cli/test_files.py`

**Closest analogs:**
1. `tests/cli/test_run.py` — CliRunner pattern
2. `tests/core/test_verifier.py` — manifest JSON construction in `tmp_path`

**Manifest fixture pattern (from `test_verifier.py`):**

```python
import json, hashlib
from pathlib import Path

def _make_manifest(tmp_path: Path, job_name: str = "test-job") -> Path:
    """Write a valid manifest.json + matching files to tmp_path."""
    content = b">seq1\nATGC\n"
    fasta_path = tmp_path / "sequences.fasta"
    fasta_path.write_bytes(content)
    sha256 = hashlib.sha256(content).hexdigest()
    manifest = {
        "manifest_version": "1.0",
        "job_name": job_name,
        "generated_at": "2026-01-01T00:00:00+00:00",
        "config": {},
        "databases": ["ncbi"],
        "stats": {"total_records": 1, "total_files": 1},
        "files": [
            {
                "path": "sequences.fasta",
                "format": "fasta",
                "sha256": sha256,
                "size": len(content),
                "record_count": 1,
                "provider": ["ncbi"],
            }
        ],
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    return tmp_path / "manifest.json"
```

---

## Files to Modify

### `src/biocurator/cli/main.py`

**Pattern (lines 22-27 — exact location to extend):**

```python
# Current state
from biocurator.cli.commands.init import init_command
from biocurator.cli.commands.run import run_command
from biocurator.cli.commands.preview import preview_command
from biocurator.cli.commands.status import status_command

app.command("init")(init_command)
app.command("run")(run_command)
app.command("preview")(preview_command)
app.command("status")(status_command)

# Phase 4 additions (append in same style)
from biocurator.cli.commands.jobs import jobs_command
from biocurator.cli.commands.files import files_command

app.command("jobs")(jobs_command)
app.command("files")(files_command)
```

---

## Key Conventions Summary

| Convention | Source | Apply To |
|-----------|--------|----------|
| `console = Console()` shared from `main.py` | `status.py` line 14 | Both commands |
| `typer.Option("--config", "-c")` | `status.py` line 22 | Both commands |
| `ConfigNotFoundError` → `console.print` + `Exit(1)` | `status.py` lines 33-36 | Both commands |
| `table.add_column("Name", style="cyan")` for primary col | `status.py` line 59 | Both commands |
| `header_style="bold magenta"` | `status.py` line 56 | Both commands |
| `[bold green]` / `[bold red]` / `[dim]` inline styling | `status.py` lines 64-82 | `files --verify` |
| `Optional[str]` argument = None | `run.py` `--jobs` adapted | `files job_name` |
| `raise typer.Exit(1)` | `run.py` line 64 | All error exits |

## PATTERN MAPPING COMPLETE
