# CLI Reference

## Global options

These options work on the `biocurator` command itself, before any subcommand.

```
biocurator [OPTIONS] COMMAND
```

| Option | Description |
|--------|-------------|
| `--version` | Print the installed version and exit. |
| `--debug` | Enable verbose INFO-level logging for all subcommands. |
| `--help` | Show help and exit. |

**Examples:**

```bash
# Print version
biocurator --version

# Run with debug logging
biocurator --debug run config.yaml
```

---

## `biocurator init`

Generate a starter config file.

```
biocurator init [OPTIONS]
```

| Option | Short | Default | Description |
|--------|-------|---------|-------------|
| `--output` | `-o` | stdout | Write the config to this file path instead of printing it. |
| `--template` | `-t` | `basic` | Template to use. `basic` includes the core fields; `advanced` includes every optional field. |

**Examples:**

```bash
# Print a basic template to the terminal
biocurator init

# Write a basic config to a file
biocurator init --output config.yaml

# Write the advanced template (all optional fields included)
biocurator init --template advanced --output config.yaml
```

---

## `biocurator run`

Execute one or more curation jobs defined in a config file.

```
biocurator run [OPTIONS] CONFIG
```

| Argument / Option | Short | Default | Description |
|-------------------|-------|---------|-------------|
| `CONFIG` | — | — | Required. Path to the YAML config file. |
| `--jobs` | `-j` | all jobs | Comma-separated list of job names to run. |
| `--dry-run` | — | off | Validate config and print a preview without downloading anything. |
| `--verbose` | `-v` | off | Print timestamped log lines to stdout during the run. |

**Examples:**

```bash
# Run all jobs in the config
biocurator run config.yaml

# Only run specific jobs
biocurator run config.yaml --jobs covid-genomes

# Run multiple specific jobs
biocurator run config.yaml --jobs covid-genomes,spike-proteins

# Preview without downloading
biocurator run config.yaml --dry-run

# Preview specific jobs
biocurator run config.yaml --jobs covid-genomes --dry-run

# Run with verbose log output
biocurator run config.yaml --verbose

# Run with debug logging (more detail than --verbose)
biocurator --debug run config.yaml
```

**Dry-run output:**

```
Dry run — 2 job(s) would execute:
  • covid-genomes       databases=['ncbi']
  • spike-proteins      databases=['uniprot']
```

**Run summary table (after a real run):**

```
           Run Summary
┌─────────────────┬────────┬──────────┐
│ Job             │ Status │ Output   │
├─────────────────┼────────┼──────────┤
│ covid-genomes   │ done   │ 2 file(s)│
│ spike-proteins  │ done   │ 1 file(s)│
└─────────────────┴────────┴──────────┘
```

---

---

## `biocurator preview`

Preview search results for a specific job without downloading sequences. This is useful for testing keywords and filters before committing to a full download.

```
biocurator preview [OPTIONS] JOB_NAME
```

| Argument / Option | Short | Default | Description |
|-------------------|-------|---------|-------------|
| `JOB_NAME` | — | — | Required. The name of the job to preview. |
| `--config` | `-c` | `config.yaml` | Path to the YAML config file. |

**Examples:**

```bash
# Preview results for 'covid-genomes' using config.yaml
biocurator preview covid-genomes

# Use a specific config file
biocurator preview spike-proteins --config tests.yaml
```

**Preview output:**

```
Previewing results for job: covid-genomes
Searching NCBI...

              Results from NCBI
┌────────────┬──────────────────────────────┬────────────┬────────┐
│ Accession  │ Title                        │ Organism   │ Length │
├────────────┼──────────────────────────────┼────────────┼────────┤
│ NC_045512  │ SARS-CoV-2 isolate Wuhan-Hu-1│ SARS-CoV-2 │  29903 │
│ MT019529   │ SARS-CoV-2 isolate 2019-nCoV │ SARS-CoV-2 │  29882 │
└────────────┴──────────────────────────────┴────────────┴────────┘
Showing 2 of 2 total matches
```

---

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Config not found, invalid config, or unknown job name |

---

Next: [[Examples]]
