---
phase: "04-cli-jobs-files-commands"
status: passed
verified: 2026-05-26T00:00:00Z
must_haves_verified: 3
must_haves_total: 3
requirements_covered: [CLI-01, CLI-02, CLI-03]
gaps: []
human_verification: []
---

# Phase 04: CLI Jobs & Files Commands — Verification Report

**Phase Goal:** Users can list available jobs from a config and inspect downloaded files with integrity verification.

**Status:** ✅ PASSED — all 3 must-haves verified against the live codebase.

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `biocurator jobs` auto-detects config and lists all jobs with Rich table | ✓ VERIFIED | `jobs.py:15-57` — `jobs_command(config="biocurator_config.yaml")` loads via `ConfigLoader.load(config)` (line 23), iterates `global_config.jobs` (line 45), renders Rich Table with 6 columns (lines 33-43), `header_style="bold magenta"` (line 37), footer with count (line 57). Registered at `main.py:50`. |
| 2 | `biocurator files my_job` lists downloaded files with metadata from manifest | ✓ VERIFIED | `files.py:68-116` — `_handle_single_job_list()`: validates job (lines 70-76), reads `manifest.json` (line 86), handles corrupt manifests (lines 87-89), renders Rich Table with Filename/Format/Size/Records/SHA-256 columns (lines 91-109), SHA-256 prefix truncated (`[:12]...` at line 108), summary footer (lines 112-116). |
| 3 | `biocurator files` (no job name) shows all-jobs summary with manifest presence | ✓ VERIFIED | `files.py:119-167` — `_handle_all_jobs_summary()`: iterates all `global_config.jobs` (line 133), checks `manifest.json` existence (line 134), renders summary table with Job/Output Dir/Files/Records/Manifest columns (lines 121-130), shows "none"/"corrupt"/✓ status per job (lines 143, 152, 160), yellow hint on no data (lines 164-167). |
| 4 | `biocurator files --verify` recomputes checksums and reports corruption | ✓ VERIFIED | `files.py:170-261` — `_handle_verify()` dispatches to `_verify_one_job()` (line 199) which calls `manifest_verify()` (line 216). Per-file status table: ✓ ok (green, line 237), ✗ corrupted (red, line 241), ? missing (yellow, line 245). All-ok branch prints "All checksums verified ✓" (line 254). Issues branch prints corrupted/missing counts (lines 257-259). Exit 1 on failure (lines 183, 204, 222). |
| 5 | All outputs use Rich tables with `header_style="bold magenta"` | ✓ VERIFIED | `jobs.py:37` (jobs table), `files.py:94` (single-job list table), `files.py:124` (all-jobs summary table), `files.py:227` (verify results table) — all 4 tables use `header_style="bold magenta"`. |

**Score:** 5/5 truths verified

---

## Requirements Coverage

### ✅ CLI-01 — `biocurator jobs` command

**Evidence:**
- `src/biocurator/cli/commands/jobs.py` line 15: `def jobs_command(config=...)` with `--config`/`-c` option defaulting to `"biocurator_config.yaml"` (line 19)
- Line 23: `global_config = ConfigLoader.load(config)` — loads config from path via `ConfigLoader.load()` in `src/biocurator/config/loader.py:17`
- Lines 24-28: `ConfigNotFoundError` caught → red error + `--config` hint → `typer.Exit(1)`
- Lines 29-31: `InvalidConfigError` caught → red error → `typer.Exit(1)`
- Lines 33-43: Rich `Table` with title="Curation Jobs", `header_style="bold magenta"`, 6 columns: Job Name / Databases / Organism / Max Results / Output Dir / Formats
- Lines 45-53: Iterates `global_config.jobs`, renders each row with database list, organism (or `[dim]—[/dim]` if None), max_results, outdir, formats
- Line 57: Footer shows job count: `f"{len(global_config.jobs)} job(s) defined in {config}"`
- `src/biocurator/cli/main.py` line 50: `app.command("jobs")(jobs_command)` — registered as CLI subcommand
- `tests/cli/test_jobs.py`: 5 tests — test_jobs_default_config_not_found, test_jobs_explicit_config_not_found, test_jobs_lists_all_jobs, test_jobs_shows_databases, test_jobs_shows_job_count

### ✅ CLI-02 — `biocurator files` list mode

**Evidence:**
- `src/biocurator/cli/commands/files.py` line 26: `def files_command(job_name=None, config="biocurator_config.yaml", verify=False)` — optional job name (line 27-30), `--config`/`-c` option (lines 31-34), `--verify` flag (lines 35-38)
- Lines 42-48: Config loading with `ConfigNotFoundError` → red error + Exit(1) and `InvalidConfigError` → red error + Exit(1)
- Lines 50-57: Dispatch: `if verify:` → `_handle_verify()`; `if job_name is not None:` → `_handle_single_job_list()`; else → `_handle_all_jobs_summary()`
- `_handle_single_job_list()` (lines 68-116):
  - Lines 70-76: Job validation — `_find_job()` lookup, unknown job → lists available job names → `typer.Exit(1)`
  - Lines 78-83: No-manifest check → yellow hint "run it with `biocurator run` first" → return (exit 0)
  - Lines 86-89: Corrupt manifest detection — `json.JSONDecodeError` / `OSError` → red error → `typer.Exit(1)`
  - Lines 91-109: Rich Table with Filename/Format/Size/Records/SHA-256 columns, `header_style="bold magenta"` (line 94)
  - Line 108: SHA-256 display: `entry["sha256"][:12] + "..."` (truncated prefix for readability)
  - Lines 112-116: Summary footer with file count, record count, generation timestamp from `manifest["stats"]`
- `_handle_all_jobs_summary()` (lines 119-167):
  - Lines 121-130: Rich Table with Job/Output Dir/Files/Records/Manifest columns, `header_style="bold magenta"` (line 124)
  - Lines 133-161: Per-job iteration: manifest exists → shows stats from `manifest["stats"]`; corrupt → shows "[bold red]corrupt[/bold red]" (line 152); missing → shows "[dim]none[/dim]" (line 160)
  - Lines 164-167: No-data warning in yellow: "No downloaded data found. Run jobs with `biocurator run` first."
- `src/biocurator/cli/main.py` line 51: `app.command("files")(files_command)` — registered as CLI subcommand
- `tests/cli/test_files.py`: 5 list-mode tests — test_files_no_manifest_shows_run_hint, test_files_shows_job_files, test_files_unknown_job_exits_error, test_files_no_job_name_shows_all_jobs, test_files_no_job_name_no_data_shows_hint

### ✅ CLI-03 — `biocurator files --verify`

**Evidence:**
- `src/biocurator/cli/commands/files.py` line 14: `from biocurator.core import manifest_verify` — imports verification library function
- Lines 50-52: `if verify: _handle_verify(job_name, global_config, config); return` — dispatch to verify path
- `_handle_verify()` (lines 170-204):
  - Single-job (lines 172-183): validates job via `_find_job()`, calls `_verify_one_job()`, exits 1 on failure
  - All-jobs (lines 185-204): collects jobs with existing manifests, iterates and runs `_verify_one_job()`, aggregates failures, exits 1 if any failure
- `_verify_one_job()` (lines 207-261):
  - Lines 210-214: No-manifest check → yellow hint "run the job first", return False (no error exit)
  - Line 216: `result = manifest_verify(manifest_path)` — delegates to core library
  - Lines 218-222: Invalid manifest → red error + `typer.Exit(1)`
  - Lines 224-249: Per-file Rich Table with Filename/Status/SHA-256 Match/Notes, color-coded: ✓ ok (green, line 237), ✗ corrupted (red, line 241), ? missing (yellow, line 245), `header_style="bold magenta"` (line 227)
  - Lines 253-254: All checks pass → green "All checksums verified ✓"
  - Lines 257-261: Issues found → red summary with corrupted/missing counts, returns True (causes `typer.Exit(1)` upstream at line 183 or 222)
- `src/biocurator/core/verifier.py` line 22: `def manifest_verify(manifest_path: Path) -> dict[str, Any]` — library function
  - Lines 46-51: Handles `json.JSONDecodeError`/`OSError` gracefully → returns structured dict with `manifest_valid: False`
  - Line 72: Security: rejects `..` path traversal entries (per RESEARCH.md V5 mitigation)
  - Lines 90-93: Chunked SHA-256 recompute using 8192-byte reads (prevents OOM on large files)
  - Lines 112-121: Returns structured dict with `all_ok`, `files_checked`, `files_matched`, `files_missing`, `files_corrupted`, `results` list
- `src/biocurator/core/__init__.py` line 1: `from biocurator.core.verifier import manifest_verify` + listed in `__all__` at line 4
- `tests/cli/test_files.py`: 4 verify-mode tests — test_files_verify_ok, test_files_verify_corrupted_exits_1, test_files_verify_missing_exits_1, test_files_verify_no_manifest_shows_hint

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `jobs_command` | `ConfigLoader.load()` | `global_config = ConfigLoader.load(config)` | ✓ WIRED | jobs.py line 23 |
| `jobs_command` | `main.py app` | `app.command("jobs")(jobs_command)` | ✓ WIRED | main.py line 50 |
| `files_command` | `ConfigLoader.load()` | `global_config = ConfigLoader.load(config)` | ✓ WIRED | files.py line 42 |
| `files_command` | `main.py app` | `app.command("files")(files_command)` | ✓ WIRED | main.py line 51 |
| `_verify_one_job` | `manifest_verify()` | `result = manifest_verify(manifest_path)` | ✓ WIRED | files.py line 216 |
| `manifest_verify` | core `__init__.py` | `from biocurator.core.verifier import manifest_verify` | ✓ WIRED | __init__.py line 1; listed in `__all__` |
| CLI error output | `typer.Exit(1)` | Non-zero exit codes on config/job/verify failures | ✓ WIRED | jobs.py:28,31; files.py:45,48,76,89,180,183,204,222 |
| Config default | `biocurator_config.yaml` | `= "biocurator_config.yaml"` in both commands | ✓ WIRED | jobs.py:19, files.py:34 |

---

## Test Results

```
$ uv run pytest tests/cli/test_jobs.py tests/cli/test_files.py -q --tb=short
..............                                                           [100%]
14 passed in 0.26s

$ uv run pytest tests/ -q --tb=short
........................................................................ [ 37%]
........................................................................ [ 75%]
..............................................                           [100%]
190 passed in 0.49s
```

**Breakdown:**
- `tests/cli/test_jobs.py`: 5 passed (CLI-01)
- `tests/cli/test_files.py`: 9 passed — 5 list-mode (CLI-02) + 4 verify-mode (CLI-03)
- Full regression suite: 190 passed, 0 failed — no regressions

---

## Anti-Patterns Found

| File | Issue | Severity | Impact |
|------|-------|----------|--------|
| *None* | | | |

All reviewed code patterns are sound:

- **Manifest corruption handled:** `files.py:87-89` catches `json.JSONDecodeError`/`OSError` with user-friendly message and `typer.Exit(1)`
- **No hardcoded paths:** All output directories derived from `job.export.outdir` in config
- **Exit codes correct:** Error paths (config not found, unknown job, corrupt manifest, checksum failure) all exit 1. Informational paths (no data, no manifest, all checksums ok) exit 0.
- **Verify flag guard:** `--verify` defaults to `False` (line 38); `verify` check at line 50 ensures verify mode only activates when explicitly requested
- **Import chain clean:** `files.py → biocurator.core (__init__.py) → biocurator.core.verifier` — no circular dependencies
- **Path traversal rejected:** `verifier.py:72` rejects `..` and absolute paths per RESEARCH.md V5 mitigation
- **Chunked file reads:** `verifier.py:92` uses 8192-byte chunks, preventing OOM on large files

---

## Requirements Traceability

| Requirement | ROADMAP Status Before | ROADMAP Status After | Evidence |
|-------------|----------------------|---------------------|----------|
| CLI-01 | `[ ]` Active | `[✓]` Validated | jobs.py:15-57 — complete implementation with tests |
| CLI-02 | `[ ]` Active | `[✓]` Validated | files.py:26-167 — list and summary modes with tests |
| CLI-03 | `[ ]` Active | `[✓]` Validated | files.py:170-261 + verifier.py:22-122 — verify mode with tests |

---

_Verified: 2026-05-26_
_Verifier: gsd-executor (parallel wave 1)_
