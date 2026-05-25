# External Integrations

**Analysis Date:** 2026-05-25

## APIs & External Services

### NCBI Entrez (E-utilities)

**What it's used for:** Searching and downloading biological sequences (nucleotide, protein, SRA, gene, literature, taxonomy) from NCBI databases.

**Provider location:** `src/biocurator/providers/ncbi/searcher.py`

**SDK/Client:** Biopython `Bio.Entrez` module (version 1.87)

**API endpoints used:**
- `Entrez.esearch` — search for records, returns ID list + history server tokens (WebEnv, QueryKey)
- `Entrez.esummary` — batch-fetch metadata summaries (accession, title, organism, length, dates)
- `Entrez.efetch` — download full FASTA sequences

**Authentication:**
- **Email** (required by NCBI policy): passed to `Entrez.email` in `src/biocurator/providers/ncbi/searcher.py` line 26
- **API Key** (optional): passed to `Entrez.api_key` from `DatabaseConfig.api_key` if configured (line 28)
- **Tool name**: `Entrez.tool = "Biocurator"` (line 27)

**Rate limiting:**
- Configurable via `DatabaseConfig.rate_limit` (default: 0.3s between requests)
- Applied as `time.sleep(self.config.rate_limit)` in both `fetch_metadata` (line 106) and `download` (line 162) loops

**Batching:**
- Metadata fetches: batched by `self.config.batch_size` (default: 20) with History Server support
- Downloads: single-record fetches (retstart/retmax per individual ID)

**Retry logic:**
- `_safe_entrez_call` decorator: `@retry(exceptions=(Exception,), max_attempts=3)` from `src/biocurator/utils/network.py`
- Internal download retry: uses a nested `@retry` decorator in the `download` method (line 142)
- History Server: search uses `usehistory="y"` so subsequent calls reference WebEnv/QueryKey instead of repeating IDs

**Error handling:**
- Catches generic `Exception` in `search()`, `fetch_metadata()`, and `download()` methods
- Returns empty lists on search failure, logs warnings on batch failures

**Query builders:** `src/biocurator/providers/ncbi/query_builders.py`
- `SequenceQueryBuilder` — for nuccore, nucleotide, protein, ipg databases (uses [Organism], [Sequence Length], [Publication Date] fielded search)
- `LiteratureQueryBuilder` — for pubmed, pmc (uses [MeSH Terms], [Title/Abstract])
- `GeneQueryBuilder` — for gene (uses [Gene/Protein Name], [Modification Date])
- `SRAQueryBuilder` — for SRA (uses [All Fields], [Organism])
- `TaxonomyQueryBuilder` — for taxonomy (uses [Scientific Name])
- Builder selection via `get_builder()` function mapping `NCBIDatabase` enum values to builder instances

**Supported databases (NCBIDatabase enum in `src/biocurator/providers/base.py`):**
- Literature: PUBMED, PMC, BOOKS, NLM_CATALOG, MESH
- Nucleotide: NUCCORE, NUCLEOTIDE, GENOME, ASSEMBLY, ANNOT_INFO, SEQ_ANNOT, SRA
- Protein: PROTEIN, IPG, PROTEIN_CLUSTERS, PROT_FAM, STRUCTURE, CDD
- Genes: GENE, SNP, DBVAR, CLINVAR, GAP, GAP_PLUS
- Chemical: PC_COMPOUND, PC_SUBSTANCE, PC_ASSAY
- Expression: GDS, GEO_PROFILES, GRASP
- Taxonomy: TAXONOMY, BIOCOLLECTIONS, ORG_TRACK
- Clinical: OMIM, MED_GEN, GTR
- Projects: BIOPROJECT, BIOSAMPLE, BLAST_DB_INFO

### UniProt REST API

**What it's used for:** Searching and downloading protein sequences from UniProtKB (Swiss-Prot/TrEMBL).

**Provider location:** `src/biocurator/providers/uniprot/searcher.py`

**SDK/Client:** Raw `requests.Session` (version 2.34.2)

**Base URL:** `https://rest.uniprot.org`

**API endpoints used:**
- `GET /uniprotkb/search` — search UniProt with query, returns TSV with accession column
- `GET /uniprotkb/accessions` — batch metadata lookup by comma-separated accessions
- `GET /uniprotkb/{uid}.fasta` — download individual FASTA sequence

**Query format (in `src/biocurator/providers/uniprot/query_builders.py`):**
- Supports: `organism:"..."`, keyword OR groups, `length:[N TO *]` / `length:[* TO N]`, `reviewed:true/false`
- Fields returned: `accession,id,protein_name,organism_name,length,date_created,date_modified,taxonomy_id`

**Authentication:**
- No API key required (public REST API)
- Email is accepted by constructor but not sent to UniProt

**Rate limiting:**
- Configurable via `DatabaseConfig.rate_limit` (default: 0.5s)
- Applied as `time.sleep(self.config.rate_limit)` in metadata fetch loop (line 86) and download loop (line 107)

**Batching:**
- Metadata: batch size capped at `min(self.config.batch_size, 25)` (line 59)
- Search: `size` param capped at `min(criteria.max_results, 500)` (line 46)

**Retry logic:**
- `_safe_get` decorator: `@retry(exceptions=(Exception,), max_attempts=3)` (line 28)
- Uses persistent `requests.Session()` for connection pooling

**Error handling:**
- `response.raise_for_status()` in `_safe_get`
- Catches generic `Exception` in all three methods (search, fetch_metadata, download)
- Returns empty list on search failure
- TSV parsing with header row detection

## Network Patterns

### Retry Decorator
**Location:** `src/biocurator/utils/network.py`

- Custom `@retry()` decorator with:
  - Configurable exception types (default: `(Exception,)`)
  - Max attempts (default: 3)
  - Exponential backoff: `initial_delay * backoff_factor^attempt` (default: 1.0s * 2.0^n)
  - Optional random jitter: `wait_time * uniform(0.5, 1.5)` when `jitter=True`
  - Logging at warning level for retries, error level for max attempts reached
- Used by both NCBI (`_safe_entrez_call`) and UniProt (`_safe_get`) providers

### HTTP Client Architecture
- **NCBI**: Uses Biopython's `Bio.Entrez` module which internally manages HTTP connections to NCBI E-utilities (`https://eutils.ncbi.nlm.nih.gov/entrez/eutils/`)
- **UniProt**: Uses `requests.Session()` for persistent HTTP/1.1 connections to `https://rest.uniprot.org`

## Data Formats

### Consumed

| Format | Where | How |
|--------|-------|-----|
| **YAML** | `config.yaml` | Input config parsed by `ConfigLoader` using `yaml.safe_load()` |
| **TSV** | UniProt API response | Tab-separated values, first line = headers, subsequent lines = records. Parsed manually via `str.split("\n")` and `str.split("\t")` |
| **FASTA** | NCBI efetch / UniProt download | Parsed by `Bio.SeqIO.read(handle, "fasta")` for single records |
| **XML** | NCBI esearch/esummary | Parsed internally by `Bio.Entrez.read(handle)` |

### Produced

| Format | Exporter Module | Output File Pattern |
|--------|----------------|---------------------|
| **FASTA** | `src/biocurator/core/exporter.py` | `{prefix}_sequences.fasta` |
| **CSV** | `src/biocurator/core/exporter.py` | `{prefix}_metadata.csv` (uses pandas) |
| **JSON** | `src/biocurator/core/exporter.py` | `{prefix}_metadata.json` (pretty-printed, JSON array of records) |

- All exports are streaming via `StreamingExporter` (file handles open during curation, close on completion)
- CSV uses pandas `DataFrame.to_csv()` per record (mode='a', header only on first write)
- JSON writes manually as `[` + `{record1},\n{record2},\n...` + `]`

## Data Storage

**File Storage:** Local filesystem only. No cloud storage or S3 integration.

**Results directory structure:** Controlled by `ExportConfig.outdir` (e.g., `results/asfv/`, `results/covid/`) with prefix-based filenames.

## Configuration Sources

**Primary:**
- YAML config file (default: `config.yaml`, configurable via CLI `--config` flag)
- Email is required at top level of config (NCBI policy requirement)
- Job definitions under `jobs:` key, each with search/filter/export sections

**No environment variables used** — all configuration comes from the YAML file.

## Webhooks & Callbacks

**None.** This is a CLI tool with no incoming/outgoing webhooks.

## CI/CD & Deployment

**Hosting:** Published to PyPI as `biocurator` Python package.

**CI Pipeline:** GitHub Actions (`.github/workflows/ci.yml` + `publish.yml`)

---

*Integration audit: 2026-05-25*
