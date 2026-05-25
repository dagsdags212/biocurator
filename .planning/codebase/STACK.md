# Technology Stack

**Analysis Date:** 2026-05-25

## Languages

**Primary:**
- Python 3.13+ — all application code

**Secondary:**
- YAML — configuration format for curation job definitions (`config.yaml`)
- Markdown — documentation

## Runtime

**Environment:**
- Python 3.13 (enforced via `.python-version` and `requires-python = ">=3.13"` in `pyproject.toml`)

**Package Manager:**
- **uv** (Astral) — fast Python package installer/resolver
- Lockfile: `uv.lock` (487 lines, all resolved versions pinned)
- Build backend: **hatchling** (`pyproject.toml` line 50: `build-backend = "hatchling.build"`)

## Frameworks

**CLI Framework:**
- **Typer** `>=0.25.1` (resolved: 0.25.1) — CLI argument parsing and command routing via `biocurator.cli.main:app`
- **Rich** `>=13.0` (resolved: 15.0.0) — terminal output: progress bars, tables, syntax highlighting, styled text

**Testing:**
- **pytest** `>=8.0` (resolved: 9.0.3) — test runner
- **pytest-mock** `>=3.0` (resolved: 3.15.1) — mock integration

**Build/Dev:**
- **hatchling** — build system and packaging
- **make** — convenience targets (`test`, `build`, `install`) in `Makefile`
- **ruff** — not explicitly in pyproject dependencies but `.ruff_cache/` directory present, indicating it is used (likely installed globally or via pre-commit)

## Key Dependencies

**Critical:**

| Package | Version Pin (pyproject) | Resolved (uv.lock) | Purpose |
|---------|------------------------|-------------------|---------|
| `biopython` | `>=1.87` | 1.87 | NCBI Entrez API wrapper (`Bio.Entrez`), FASTA/GenBank parsing (`Bio.SeqIO`) |
| `requests` | `>=2.34.2` | 2.34.2 | HTTP client for UniProt REST API |
| `pandas` | `>=3.0.3` | 3.0.3 | Metadata CSV export, DataFrame construction |
| `numpy` | `>=2.0` | 2.4.4 | Transitive dependency of biopython/pandas, quality score calculations |
| `pyyaml` | `>=6.0` | 6.0.3 | YAML config file parsing (`config.yaml`) |
| `typer` | `>=0.25.1` | 0.25.1 | CLI framework (subcommands: `init`, `run`, `preview`) |
| `rich` | `>=13.0` | 15.0.0 | Terminal UI: progress bars, tables, styled output, syntax highlighting |

**Infrastructure (transitive, all resolved from uv.lock):**

| Package | Resolved Version |
|---------|-----------------|
| `click` | 8.3.3 |
| `certifi` | 2026.4.22 |
| `urllib3` | 2.7.0 |
| `charset-normalizer` | 3.4.7 |
| `idna` | 3.15 |
| `colorama` | 0.4.6 |
| `markdown-it-py` | 4.2.0 |
| `mdurl` | 0.1.2 |
| `pygments` | 2.20.0 |
| `shellingham` | 1.5.4 |
| `python-dateutil` | 2.9.0.post0 |
| `tzdata` | 2026.2 |
| `six` | 1.17.0 |
| `iniconfig` | 2.3.0 |
| `packaging` | 26.2 |
| `pluggy` | 1.6.0 |
| `annotated-doc` | 0.0.4 |

## Configuration

**Environment:**
- No `.env` files used
- No environment variables required at runtime
- Email for NCBI API access is passed via CLI or YAML config, not env vars

**Application Config:**
- YAML file (`config.yaml`) loaded at runtime via `ConfigLoader` in `src/biocurator/config/loader.py`
- Config schema defined via dataclasses in `src/biocurator/config/schema.py`:
  - `GlobalConfig` — email + list of `JobConfig`
  - `JobConfig` — name + `SearchConfig` + `FilterConfig` + `ExportConfig`
  - `SearchConfig` — databases, organism, sequence_type, keywords, max_results, date_range, etc.
  - `FilterConfig` — min/max length, exclude_terms, quality_threshold
  - `ExportConfig` — outdir, formats, prefix

**Build:**
- `pyproject.toml` — single source of truth for project metadata, dependencies, build config
- No `setup.py`, `setup.cfg`, or `tox.ini`

## Platform Requirements

**Development:**
- Python >= 3.13
- uv (package manager)
- make (optional, for convenience targets)
- No Docker container

**Production:**
- Published to PyPI as `biocurator` package
- CLI entry point: `biocurator` (defined in `[project.scripts]`)
- No server/deployment — runs as a local CLI tool

## CI/CD

**Continuous Integration (`.github/workflows/ci.yml`):**
- Triggers: push/PR to `main`
- Strategy: Python 3.13 on ubuntu-latest
- Steps:
  1. `actions/checkout@v4.2.2`
  2. `astral-sh/setup-uv@v6` with cache enabled
  3. Install Python 3.13 via `uv python install`
  4. Install dependencies: `uv sync --frozen`
  5. Run tests: `uv run pytest -v --tb=short`

**Publishing (`.github/workflows/publish.yml`):**
- Triggers: GitHub Release published
- Two jobs (test -> publish):
  - **test**: same as CI (Python 3.13, uv sync, pytest)
  - **publish**: `uv build` then `pypa/gh-action-pypi-publish@release/v1` with `secrets.PYPI_TOKEN`

---

*Stack analysis: 2026-05-25*
