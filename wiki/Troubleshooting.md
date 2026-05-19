# Troubleshooting

## Config errors

### `InvalidConfigError: 'email' is required`

Your config file is missing the top-level `email` field.

**Fix:** Add it as the very first line:

```yaml
email: your@email.com

jobs:
  ...
```

---

### `ConfigNotFoundError`

biocurator cannot find the config file at the path you provided.

**Fix:** Double-check the path:

```bash
# Wrong
biocurator run configs/myconfig.yml

# Check what exists
ls configs/

# Correct
biocurator run configs/myconfig.yaml
```

Use `--dry-run` to validate a path without downloading:

```bash
biocurator run config.yaml --dry-run
```

---

### `InvalidConfigError: unknown job "my-job"`

You used `--jobs` with a job name that is not in the config.

**Fix:** Check the exact job name in your config (names are case-sensitive):

```yaml
jobs:
  covid-genomes:   # this is the name to pass to --jobs
    ...
```

```bash
biocurator run config.yaml --jobs covid-genomes
```

---

## Search returns no sequences

**Symptoms:** The run completes but output files are empty or contain zero sequences.

**Checklist:**

1. **Organism name** — must match NCBI or UniProt taxonomy exactly.
   - Wrong: `"sars cov 2"`
   - Right: `"SARS-CoV-2"`

2. **Keywords too narrow** — try removing keywords one by one or broadening them.

3. **Exclusion terms too aggressive** — check whether your `exclude_terms` are filtering out valid results.

4. **`max_results` too low** — increase it:
   ```yaml
   max_results: 500
   ```

5. **Date range** — verify the format is `YYYY/MM/DD` and the range actually contains records.

6. **Dry-run to confirm config is valid before blaming the search:**
   ```bash
   biocurator run config.yaml --dry-run
   ```

---

## All sequences filtered out

**Symptoms:** Search finds records but the FASTA is empty.

This usually means the filter settings are too strict.

**Checklist:**

1. `min_length` or `max_length` — is your target sequence actually in that range?
2. `quality_threshold` — lower it (e.g. from `0.99` to `0.9`) to confirm it is the cause.
3. `filter.exclude_terms` — one of these terms may match records you intended to keep.

**Debug tip:** Run without filters first to see how many raw sequences come back:

```yaml
filter: {}
```

Then add filters back one at a time.

---

## NCBI rate-limit errors

**Symptoms:** `DatabaseSearchError` or slow runs with HTTP 429 responses in the logs.

NCBI enforces 3 requests/second for anonymous access. biocurator already respects this limit, but very large jobs (`max_results: 1000+`) will naturally take longer.

**What to do:**
- Be patient — large jobs may take several minutes.
- Enable verbose logging to see progress:
  ```bash
  biocurator run config.yaml --verbose
  ```

---

## Debug logging

For detailed output on what biocurator is doing internally, use the `--debug` global flag:

```bash
biocurator --debug run config.yaml
```

This prints INFO-level log messages including API calls, filter decisions, and file writes.

For a lighter version that only logs during a run:

```bash
biocurator run config.yaml --verbose
```

Log format:
```
2026-05-18 14:32:01  INFO      Searching NCBI for SARS-CoV-2...
2026-05-18 14:32:03  INFO      Found 47 records, applying filters...
2026-05-18 14:32:03  INFO      42 records passed filters
2026-05-18 14:32:08  INFO      Downloaded 42 sequences
2026-05-18 14:32:08  INFO      Exported results/covid/sars_cov2_sequences.fasta
```

---

## Still stuck?

Open an issue on the [GitHub issue tracker](https://github.com/dagsdags212/biocurator/issues) and include:

- Your config file (remove your email)
- The exact command you ran
- The full error output (use `--debug` to capture more detail)
