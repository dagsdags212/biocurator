# Phase 4 Research: CLI Jobs & Files Commands

**Researched:** 2026-05-26
**Phase:** 4 — CLI Jobs & Files Commands
**Requirements:** CLI-01, CLI-02, CLI-03

---

## 1. Existing CLI Architecture

### Command Registration Pattern

All commands follow the same function-based pattern registered to the Typer `app` in `main.py`:

```python
# src/biocurator/cli/main.py
app.command("init")(init_command)
app.command("run")(run_command)
app.command("preview")(preview_command)
app.command("status")(status_command)
```

Each command lives in `src/biocurator/cli/commands/{name}.py` as a standalone function. New commands for Phase 4 follow the same pattern:

- `src/biocurator/cli/commands/jobs.py` → `jobs_command` function
- `src/biocurator/cli/commands/files.py` → `files_command` function
- Both registered in `main.py`

### Imports Available in Commands

All commands import from `biocurator.cli.main` the shared `console = Console()` object. Standard imports:

```python
from typing import Annotated, Optional
import typer
from rich.table import Table
from biocurator.cli.main import console
from biocurator.config.loader import ConfigLoader
from biocurator.exceptions import ConfigNotFoundError, InvalidConfigError
```

### Status Command as Canonical Analog

`src/biocurator/cli/commands/status.py` is the closest analog: it accepts `--config`/`-c`, loads with `ConfigLoader.load()`, catches `ConfigNotFoundError` and `InvalidConfigError`, and renders a Rich `Table` with styled columns. Phase 4 commands must replicate this exact error-handling pattern.

---

## 2. Config Loading and Schema

### ConfigLoader Behavior

```python
ConfigLoader.load(path: str | Path) -> GlobalConfig
```

- Raises `ConfigNotFoundError` if file doesn't exist
- Raises `InvalidConfigError` for bad YAML or missing required fields
- Returns `GlobalConfig(email, jobs: list[JobConfig], retry, breaker)`

### JobConfig Fields Available for Display

```python
@dataclass
class JobConfig:
    name: str
    search: SearchConfig  # .databases (list[str]), .organism, .max_results
    filter: FilterConfig  # .min_length, .max_length
    export: ExportConfig  # .outdir (str), .formats (list[str]), .prefix (str)
```

For `biocurator jobs` table columns: `name`, `search.databases`, `search.organism`, `search.max_results`, `export.outdir`, `export.formats`.

### Default Config Filename

The ROADMAP specifies: `biocurator_config.yaml` in CWD (not `config.yaml`). The `status` and `run` commands use `config.yaml` as default, but the ROADMAP requirement for `biocurator jobs` explicitly calls for `biocurator_config.yaml`. Phase 4 must use `biocurator_config.yaml` as the default for both `jobs` and `files` commands.

---

## 3. Manifest JSON Schema (Phase 3 Output)

The `StreamingExporter._write_manifest()` writes to `{outdir}/manifest.json`:

```json
{
  "manifest_version": "1.0",
  "job_name": "my-job",
  "generated_at": "2026-05-25T10:00:00+00:00",
  "config": { ... },
  "databases": ["ncbi"],
  "stats": {
    "total_records": 42,
    "total_files": 2
  },
  "files": [
    {
      "path": "biocurator_sequences.fasta",
      "format": "fasta",
      "sha256": "abc123...",
      "size": 10240,
      "record_count": 42,
      "provider": ["ncbi"]
    },
    {
      "path": "biocurator_metadata.csv",
      "format": "csv",
      "sha256": "def456...",
      "size": 5120,
      "record_count": 42,
      "provider": ["ncbi"]
    }
  ]
}
```

### Where Manifests Live

Each job has `export.outdir` (string, e.g. `"results"` or `"./output/my-job"`). The manifest is always at `Path(export.outdir) / "manifest.json"`. This is a relative path resolved from CWD at runtime.

### Companion File

Also written: `{outdir}/manifest-sha256.txt` — BagIt-compatible format: `{sha256}  {filename}` per line. Not needed for Phase 4 CLI display, but relevant context.

---

## 4. manifest_verify() API (Phase 3 Library Function)

Located in `src/biocurator/core/verifier.py`, exported via `src/biocurator/core/__init__.py`:

```python
from biocurator.core import manifest_verify

result = manifest_verify(manifest_path: Path) -> dict[str, Any]
```

**Return schema:**

```python
{
    "manifest_path": str,
    "manifest_valid": bool,       # False if JSON unreadable
    "files_checked": int,
    "files_matched": int,
    "files_missing": int,
    "files_corrupted": int,
    "all_ok": bool,               # True iff files_checked > 0 and all matched
    "results": [
        {
            "path": str,          # relative filename (e.g. "biocurator_sequences.fasta")
            "sha256_expected": str,
            "sha256_actual": str | None,   # None if file missing
            "status": "ok" | "corrupted" | "missing"
        },
        ...
    ]
}
```

**Security:** Path traversal entries (`../etc/passwd`) are silently skipped by the library. No additional sanitization needed in the CLI layer.

---

## 5. Command Design

### `biocurator jobs` (CLI-01)

**Signature:**

```python
def jobs_command(
    config: Annotated[
        str,
        typer.Option("--config", "-c", help="Path to the YAML config file"),
    ] = "biocurator_config.yaml",
) -> None:
```

**Behavior:**
1. Load config with `ConfigLoader.load(config)` — catch `ConfigNotFoundError`/`InvalidConfigError`
2. Iterate `global_config.jobs`
3. Render Rich Table: columns = `Job Name`, `Databases`, `Organism`, `Max Results`, `Output Dir`, `Formats`
4. Footer: `{N} job(s) defined in {config}`

**Error case**: If default `biocurator_config.yaml` not found → message must say "Config file not found — specify a path with --config" (clear direction per CLI-01 requirement).

### `biocurator files` (CLI-02, CLI-03)

**Signature:**

```python
def files_command(
    job_name: Annotated[
        Optional[str],
        typer.Argument(help="Job name to inspect (omit to show all jobs with data)"),
    ] = None,
    config: Annotated[
        str,
        typer.Option("--config", "-c", help="Path to the YAML config file"),
    ] = "biocurator_config.yaml",
    verify: Annotated[
        bool,
        typer.Option("--verify", help="Re-read files and verify SHA-256 checksums"),
    ] = False,
) -> None:
```

**Behavior — no `job_name` (show all jobs with data):**
1. Load config, get all jobs
2. For each job, check `Path(job.export.outdir) / "manifest.json"` exists
3. Render summary table: `Job Name`, `Output Dir`, `Files`, `Total Records`, `Has Manifest`
4. If no manifests found: "No downloaded data found. Run `biocurator run` first."

**Behavior — `job_name` provided:**
1. Load config, find matching job (raise error if not found)
2. Load `{export.outdir}/manifest.json` — if missing: "No data for job '{name}' — run it first."
3. Render file table: `Filename`, `Format`, `Size`, `Records`, `SHA-256 (short)`
4. Footer: `{N} file(s), {total_records} total records — {generated_at}`

**Behavior — `--verify` (with or without `job_name`):**
1. Determine which jobs to verify (one or all with manifests)
2. For each: call `manifest_verify(manifest_path)`
3. Render verification table: `Filename`, `Status (✓/✗/?)`, `SHA-256 Match`, `Notes`
4. Color coding: ok → green, corrupted → red, missing → yellow
5. Footer: `all_ok` → "[bold green]All checksums verified ✓[/bold green]"  
          not all_ok → "[bold red]Corruption detected — see above[/bold red]"
6. Exit code 1 if any file is corrupted or missing (so scripting can detect failure)

---

## 6. Rich Table Patterns (from status.py)

```python
table = Table(
    title="Job List",
    show_header=True,
    header_style="bold magenta",
)
table.add_column("Job Name", style="cyan")
table.add_column("Databases")
table.add_column("Organism")
table.add_column("Max Results", justify="right")
table.add_column("Output Dir")
console.print(table)
```

Inline styling for status values (mirror status.py):
- Green: `"[bold green]text[/bold green]"`
- Red: `"[bold red]text[/bold red]"`
- Yellow: `"[bold yellow]text[/bold yellow]"`
- Dim/NA: `"[dim]N/A[/dim]"`

Size formatting: human-readable (1024 → `1.0 KB`) — use simple inline division, no stdlib import needed.

---

## 7. File Size Formatting

Manifest stores `size` in bytes. Display human-readable:

```python
def _format_size(size_bytes: int) -> str:
    if size_bytes >= 1_048_576:
        return f"{size_bytes / 1_048_576:.1f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes} B"
```

SHA-256 display: truncate to first 12 chars + `...` for table display. Full hash shown only in verify mode.

---

## 8. Error Handling Strategy

| Scenario | Response |
|----------|----------|
| Config file not found (default `biocurator_config.yaml`) | Print error, include `--config` hint, exit 1 |
| Config file not found (explicit path) | Print error with exact path, exit 1 |
| Job name not in config | Print "Unknown job: {name}. Available: {names}", exit 1 |
| Manifest missing for a job | Print "No data for '{name}' — run first", exit 0 (not an error) |
| Manifest invalid JSON | Print "Cannot read manifest: {path}", exit 1 |
| Checksum mismatch | Print table with red row, exit 1 |
| All checksums OK | Print table with green rows, exit 0 |

---

## 9. Implementation Files

### New Files to Create

| File | Purpose |
|------|---------|
| `src/biocurator/cli/commands/jobs.py` | `jobs_command` implementation |
| `src/biocurator/cli/commands/files.py` | `files_command` implementation |
| `tests/cli/test_jobs.py` | Unit tests for jobs command |
| `tests/cli/test_files.py` | Unit tests for files command |

### Files to Modify

| File | Change |
|------|--------|
| `src/biocurator/cli/main.py` | Import + register `jobs_command`, `files_command` |
| `src/biocurator/cli/commands/__init__.py` | No change needed (not re-exported) |

---

## 10. Dependencies on Phase 3

Phase 4 directly depends on:
- `src/biocurator/core/verifier.py` — `manifest_verify()` (already public via `__init__.py`)
- `src/biocurator/core/exporter.py` — manifest schema (no code dependency, but schema must match)

No new library dependencies required. All tools (Typer, Rich, pathlib, json) are already in `pyproject.toml`.

---

## 11. Validation Architecture

### What Needs Tests

| Test File | Tests | Strategy |
|-----------|-------|----------|
| `tests/cli/test_jobs.py` | ~5 tests | `CliRunner` + real YAML in `tmp_path` |
| `tests/cli/test_files.py` | ~8 tests | `CliRunner` + real YAML + real JSON manifests in `tmp_path` |

### `test_jobs.py` Test Cases

1. **`test_jobs_default_config_not_found`** — invoke `jobs` with no args when no `biocurator_config.yaml` exists → exit code ≠ 0, output contains `--config` hint
2. **`test_jobs_lists_all_jobs`** — write a valid config to `tmp_path`, invoke `jobs --config {path}` → exit 0, output contains job names
3. **`test_jobs_missing_explicit_config`** — invoke `jobs --config nonexistent.yaml` → exit ≠ 0, output contains "not found"
4. **`test_jobs_empty_jobs_block_invalid`** — config with empty jobs mapping → exit ≠ 0 (InvalidConfigError)
5. **`test_jobs_multiple_jobs_all_shown`** — two-job config → both names appear in output

### `test_files.py` Test Cases

1. **`test_files_no_manifest_exists`** — config with job, no manifest written → exit 0, message says "No downloaded data" or similar
2. **`test_files_shows_job_files`** — write manifest.json to `export.outdir`, invoke `files job-a --config ...` → exit 0, manifest file entries in output
3. **`test_files_unknown_job_name`** — invoke `files unknown-job --config ...` → exit ≠ 0, "Unknown job" in output
4. **`test_files_no_job_name_shows_all`** — two jobs, one with manifest, one without → summary table shown, both rows present
5. **`test_files_verify_ok`** — write manifest + matching files → `files --verify --config ...` → exit 0, "All checksums verified" in output
6. **`test_files_verify_corrupted`** — write manifest with wrong checksum → exit 1, "corrupted" in output
7. **`test_files_verify_missing`** — write manifest referencing non-existent file → exit 1, "missing" in output
8. **`test_files_invalid_manifest`** — write non-JSON manifest.json → exit ≠ 0, error message about manifest

### Testing Pattern (from `tests/cli/test_run.py`)

```python
from typer.testing import CliRunner
from biocurator.cli.main import app

runner = CliRunner()

def test_example(tmp_path):
    cfg = tmp_path / "biocurator_config.yaml"
    cfg.write_text(VALID_CONFIG)
    manifest_dir = tmp_path / "results"
    manifest_dir.mkdir()
    (manifest_dir / "manifest.json").write_text(json.dumps(VALID_MANIFEST))

    result = runner.invoke(app, ["files", "--config", str(cfg)])
    assert result.exit_code == 0
    assert "job-name" in result.output
```

No mocking of `ConfigLoader` or `manifest_verify` needed — tests use real files in `tmp_path`. This matches Phase 3's `test_verifier.py` pattern (real files, real functions).

### Fixtures Strategy

Define `VALID_CONFIG` and `VALID_MANIFEST` as module-level strings/dicts in each test file (same approach as `test_run.py`). No shared conftest.py fixtures needed.

---

## 12. Risk Areas

| Risk | Mitigation |
|------|-----------|
| Relative `export.outdir` paths resolved from wrong CWD in tests | Use `tmp_path` for outdir AND set outdir to absolute path in test config |
| `biocurator_config.yaml` default name conflicts with existing `config.yaml` convention | Both commands explicitly use `biocurator_config.yaml` default only; error message shows the actual path tried |
| `--verify` exit code 1 breaks scripts expecting 0 even on warnings | Only exit 1 for corrupted/missing; exit 0 when manifest_valid=False but files_checked=0 (edge case: empty manifest) |
| `files` (no job_name) with no config → unclear error | Consistent error: "Config file not found: biocurator_config.yaml — specify with --config" |

---

## 13. Wave Breakdown Recommendation

**Wave 1 (independent):**
- Plan 04-01: `jobs_command` + main.py registration + tests

**Wave 2 (independent, can parallel with Wave 1):**
- Plan 04-02: `files_command` (list mode) + main.py registration + tests

**Wave 3 (depends on Wave 2 — needs files command infrastructure):**
- Plan 04-03: `files --verify` mode + verify exit codes + tests

Or alternatively, Wave 1 and Wave 2 can be combined if plans are kept short (~8-10 tasks each).

---

*Research complete — ready for planning*
