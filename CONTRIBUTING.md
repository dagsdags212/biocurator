<!-- generated-by: gsd-doc-writer -->
# Contributing to Biocurator

## Quick Start

```bash
git clone https://github.com/dagsdags212/biocurator.git
cd biocurator
uv pip install -e .
make test   # verify all tests pass before making changes
```

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for full setup and conventions.

## Commit Message Conventions

| Prefix | Use for |
|--------|---------|
| `feat:` | New user-facing feature |
| `fix:` | Bug fix |
| `refactor:` | Restructuring without behaviour change |
| `test:` | Adding or updating tests |
| `docs:` | Documentation only |
| `build:` | Build system, deps, packaging |
| `chore:` | Housekeeping (version bump, CI config) |

Keep subject lines under 72 characters. Example: `feat: add ENA provider for European Nucleotide Archive`.

## Pull Request Checklist

Before submitting a PR:

- [ ] Branch from `main` with a descriptive name (e.g. `feat/ena-provider`)
- [ ] `make test` passes with no failures
- [ ] `uv run ruff check src/ tests/` exits cleanly
- [ ] New behaviour is covered by tests (see [docs/TESTING.md](docs/TESTING.md))
- [ ] CLI or config changes are reflected in the relevant doc

## Coding Standards

- Ruff `line-length = 100`, rules `E`, `F`, `I`
- All public functions must have type annotations
- Raise specific exceptions from `exceptions.py`, never bare `Exception`
- Per-record failures: log as `warning` and skip — never abort the batch
- No real API calls in tests — always mock `Bio.Entrez` / `requests`

## Reporting Issues

Open an issue at `https://github.com/dagsdags212/biocurator/issues`. Include:

- OS, Python version, and `pip show biocurator` output
- The YAML config used (redact your email)
- Full command and error traceback

## License

By contributing, you agree your changes will be licensed under the [MIT License](LICENSE) that covers this project.
