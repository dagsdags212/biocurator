---
plan: "04-01"
phase: "04"
status: complete
completed: "2026-05-26"
commits:
  - 2cd0927
  - fa58082
key_files:
  created:
    - src/biocurator/cli/commands/jobs.py
    - tests/cli/test_jobs.py
  modified:
    - src/biocurator/cli/main.py
requirements_addressed:
  - CLI-01
---

# Plan 04-01 Summary: biocurator jobs command

## What Was Built

Implemented `biocurator jobs [--config PATH]` CLI command. The command loads the specified YAML config (defaulting to `biocurator_config.yaml`), reads all defined jobs, and renders a Rich table with columns: Job Name, Databases, Organism, Max Results, Output Dir, and Formats. Exits non-zero with a `--config` hint if the default config is not found.

## Tasks Completed

| Task | Description | Commit |
|------|-------------|--------|
| 04-01-01 | Create jobs_command in jobs.py | 2cd0927 |
| 04-01-02 | Register app.command("jobs") in main.py | 2cd0927 |
| 04-01-03 | Write 5 unit tests in tests/cli/test_jobs.py | fa58082 |

## Verification

```
uv run pytest tests/cli/test_jobs.py -q
# → 5 passed
python -c "from biocurator.cli.main import app; print('import OK')"
# → import OK
```

## Deviations

None — plan executed exactly as specified.

## Self-Check: PASSED

- src/biocurator/cli/commands/jobs.py: EXISTS
- jobs_command registered in main.py: CONFIRMED
- tests/cli/test_jobs.py: EXISTS with 5 test functions
- pytest tests/cli/test_jobs.py: 5 passed
- Import check: OK
