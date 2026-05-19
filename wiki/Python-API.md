# Python API

biocurator can be used directly from Python if you want to embed curation into a larger script or notebook.

## Core classes

| Class | Import path | Purpose |
|-------|-------------|---------|
| `Biocurator` | `biocurator.core.curator` | Runs jobs |
| `JobConfig` | `biocurator.config.schema` | Describes a single job |
| `SearchConfig` | `biocurator.config.schema` | Search parameters |
| `FilterConfig` | `biocurator.config.schema` | Filter parameters |
| `ExportConfig` | `biocurator.config.schema` | Output parameters |
| `ConfigLoader` | `biocurator.config.loader` | Loads a YAML file into a `GlobalConfig` |

---

## Running a single job

```python
from biocurator.core.curator import Biocurator
from biocurator.config.schema import JobConfig, SearchConfig, FilterConfig, ExportConfig

job = JobConfig(
    name="my-job",
    search=SearchConfig(
        databases=["ncbi"],
        organism="SARS-CoV-2",
        sequence_type="nucleotide",
        keywords=["complete genome"],
        max_results=10,
    ),
    filter=FilterConfig(min_length=29000, quality_threshold=0.8),
    export=ExportConfig(outdir="results", formats=["fasta", "csv"], prefix="sars"),
)

curator = Biocurator(email="your@email.com")
output_files = curator.run_job(job)

print(output_files)
# {"fasta": PosixPath("results/sars_sequences.fasta"), "csv": PosixPath("results/sars_metadata.csv")}
```

`run_job` returns a dict mapping format name → output `Path`.

---

## Tracking progress with a callback

Pass a callback to receive updates as each phase completes. The callback receives three arguments: `phase` (string), `current` (int), and `total` (int).

```python
def on_progress(phase: str, current: int, total: int):
    print(f"[{phase}] {current}/{total}")

curator.run_job(job, progress_callback=on_progress)
```

Example output:
```
[search] 1/4
[filter] 2/4
[download] 3/4
[export] 4/4
```

---

## Loading a config file

If you already have a `config.yaml`, load it programmatically instead of building configs by hand:

```python
from biocurator.config.loader import ConfigLoader
from biocurator.core.curator import Biocurator

config = ConfigLoader.load("config.yaml")
curator = Biocurator(email=config.email)

for job in config.jobs:
    output_files = curator.run_job(job)
    print(f"{job.name}: {list(output_files)}")
```

---

## Running only specific jobs from a config

```python
from biocurator.config.loader import ConfigLoader
from biocurator.core.curator import Biocurator

config = ConfigLoader.load("config.yaml")
curator = Biocurator(email=config.email)

target_names = {"spike-proteins", "nucleocapsid-proteins"}
selected = [j for j in config.jobs if j.name in target_names]

for job in selected:
    output_files = curator.run_job(job)
    print(f"{job.name}: {output_files}")
```

---

## Handling exceptions

All biocurator errors inherit from `BiocuratorError`, so you can catch the base class or specific subclasses:

```python
from biocurator.exceptions import (
    BiocuratorError,
    ConfigNotFoundError,
    InvalidConfigError,
    JobNotFoundError,
    DatabaseSearchError,
    DownloadError,
    ExportError,
)
from biocurator.config.loader import ConfigLoader
from biocurator.core.curator import Biocurator
from biocurator.config.schema import JobConfig, SearchConfig, FilterConfig, ExportConfig

# Catch a specific error
try:
    config = ConfigLoader.load("missing.yaml")
except ConfigNotFoundError as e:
    print(f"Config file not found: {e}")

# Catch any biocurator error
try:
    curator = Biocurator(email="your@email.com")
    curator.run_job(job)
except DatabaseSearchError as e:
    print(f"Search failed: {e}")
except DownloadError as e:
    print(f"Download failed: {e}")
except BiocuratorError as e:
    print(f"Unexpected error: {e}")
```

### Exception reference

| Exception | When it is raised |
|-----------|------------------|
| `ConfigNotFoundError` | The YAML file path does not exist |
| `InvalidConfigError` | The YAML is malformed or missing required fields |
| `JobNotFoundError` | A requested job name is not in the config |
| `DatabaseSearchError` | The API call to NCBI or UniProt failed |
| `DownloadError` | Downloading sequences failed |
| `ExportError` | Writing output files to disk failed |

---

## Example: batch processing multiple organisms

```python
from biocurator.core.curator import Biocurator
from biocurator.config.schema import JobConfig, SearchConfig, FilterConfig, ExportConfig

organisms = [
    "SARS-CoV-2",
    "MERS-CoV",
    "Influenza A virus",
]

curator = Biocurator(email="your@email.com")

for organism in organisms:
    safe_name = organism.lower().replace(" ", "_").replace("-", "_")
    job = JobConfig(
        name=safe_name,
        search=SearchConfig(
            databases=["ncbi"],
            organism=organism,
            sequence_type="nucleotide",
            keywords=["complete genome"],
            max_results=50,
        ),
        filter=FilterConfig(quality_threshold=0.9),
        export=ExportConfig(
            outdir=f"results/{safe_name}",
            formats=["fasta", "csv"],
            prefix=safe_name,
        ),
    )
    output_files = curator.run_job(job)
    print(f"{organism}: {[str(p) for p in output_files.values()]}")
```

---

Next: [[Output Files]]
