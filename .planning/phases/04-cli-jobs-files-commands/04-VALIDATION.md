---
phase: 4
slug: cli-jobs-files-commands
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-26
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `uv run pytest tests/cli/test_jobs.py tests/cli/test_files.py -q` |
| **Full suite command** | `uv run pytest -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/cli/test_jobs.py tests/cli/test_files.py -q`
- **After every plan wave:** Run `uv run pytest -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Secure Behavior | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------------|-----------|-------------------|--------|
| 04-01-01 | 01 | 1 | CLI-01 | `jobs_command` created in commands/jobs.py | unit | `pytest tests/cli/test_jobs.py -q` | ⬜ pending |
| 04-01-02 | 01 | 1 | CLI-01 | Registered in main.py as `app.command("jobs")` | unit | `pytest tests/cli/test_jobs.py -q` | ⬜ pending |
| 04-01-03 | 01 | 1 | CLI-01 | Default config `biocurator_config.yaml`; clear error if missing | unit | `pytest tests/cli/test_jobs.py::test_jobs_default_config_not_found -q` | ⬜ pending |
| 04-01-04 | 01 | 1 | CLI-01 | Rich table shows all job names, databases, output dir | unit | `pytest tests/cli/test_jobs.py::test_jobs_lists_all_jobs -q` | ⬜ pending |
| 04-02-01 | 02 | 1 | CLI-02 | `files_command` created in commands/files.py | unit | `pytest tests/cli/test_files.py -q` | ⬜ pending |
| 04-02-02 | 02 | 1 | CLI-02 | Registered in main.py as `app.command("files")` | unit | `pytest tests/cli/test_files.py -q` | ⬜ pending |
| 04-02-03 | 02 | 1 | CLI-02 | `files job-name` reads manifest, displays file table | unit | `pytest tests/cli/test_files.py::test_files_shows_job_files -q` | ⬜ pending |
| 04-02-04 | 02 | 1 | CLI-02 | `files` (no args) shows all jobs with data | unit | `pytest tests/cli/test_files.py::test_files_no_job_name_shows_all -q` | ⬜ pending |
| 04-02-05 | 02 | 1 | CLI-02 | Missing manifest → graceful "run first" message, exit 0 | unit | `pytest tests/cli/test_files.py::test_files_no_manifest_exists -q` | ⬜ pending |
| 04-03-01 | 03 | 2 | CLI-03 | `--verify` calls `manifest_verify()`, renders verify table | unit | `pytest tests/cli/test_files.py::test_files_verify_ok -q` | ⬜ pending |
| 04-03-02 | 03 | 2 | CLI-03 | Corrupted file → red row, exit 1 | unit | `pytest tests/cli/test_files.py::test_files_verify_corrupted -q` | ⬜ pending |
| 04-03-03 | 03 | 2 | CLI-03 | Missing file → yellow row, exit 1 | unit | `pytest tests/cli/test_files.py::test_files_verify_missing -q` | ⬜ pending |
| 04-03-04 | 03 | 2 | CLI-03 | All ok → green summary, exit 0 | unit | `pytest tests/cli/test_files.py::test_files_verify_ok -q` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/cli/test_jobs.py` — stubs/structure for CLI-01 tests
- [ ] `tests/cli/test_files.py` — stubs/structure for CLI-02 and CLI-03 tests

*Framework and conftest already exist. No new infrastructure needed beyond the two test files.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Rich table renders correctly in terminal | CLI-01, CLI-02 | CliRunner strips Rich markup; visual formatting untestable | Run `biocurator jobs --config tests/fixtures/sample.yaml` and verify table layout |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
