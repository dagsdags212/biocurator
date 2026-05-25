# Technology Stack — Reliability Additions

**Project:** Biocurator
**Researched:** 2026-05-25
**Scope:** Reliability improvements (circuit breakers, configurable retry, health checks, checksum verification, manifest tracking, CLI status commands) for an existing Python 3.13+ CLI tool using NCBI Entrez and UniProt REST APIs.

## Context

This is a **subsequent milestone** on an existing codebase (v0.2.0). These recommendations **add to** the existing stack, not replace it. The current stack is already established:

| Layer | Current | Status |
|-------|---------|--------|
| CLI framework | Typer 0.25.1 + Rich 15.0.0 | ✅ Existing |
| HTTP client | requests 2.34.2 | ✅ Existing |
| NCBI API wrapper | biopython 1.87 (`Bio.Entrez`) | ✅ Existing |
| Retry | Custom `@retry` decorator in `utils/network.py` | ❌ Needs upgrade |
| Circuit breaker | None | ❌ Needs addition |
| Health checks | None | ❌ Needs addition |
| Checksum verification | None | ❌ Needs addition |
| Manifest tracking | None | ❌ Needs addition |
| Database config | `DatabaseConfig` with `rate_limit`, `timeout`, `batch_size` | ✅ Existing, needs extension |

## Recommended Additions

### 1. Retry — tenacity v9.x

**Verdict: Replace the custom `@retry` decorator with tenacity.**

| Aspect | Detail |
|--------|--------|
| **Library** | `tenacity` >= 9.1.0 |
| **Current version** | 9.1.4 (released 2026-02-07) |
| **Python support** | >= 3.10 (compatible with project's 3.13+) |
| **Monthly downloads** | ~389M |
| **License** | Apache 2.0 |
| **Confidence** | HIGH |

**Why tenacity over alternatives:**

| Option | Verdict | Reason |
|--------|---------|--------|
| **tenacity** | ✅ **Recommended** | Actively maintained (9 releases in 2025-2026), richest API, 389M monthly downloads, 9K GitHub stars. Full stop/wait/retry condition combinatorics. |
| **backoff** | ❌ Not recommended | Original repo (`litl/backoff`) archived since 2024. Fork (`python-backoff`) at v2.3.1 has only 25 stars. Last meaningful release 2022. No circuit breaker integration. |
| **Custom (current)** | ❌ Insufficient for this milestone | Current 80-line decorator works but: (a) hardcodes `max_attempts=3` at every call site, (b) no per-provider configurability, (c) no retry statistics/state exposure, (d) no async support, (e) no `before_sleep` logging hooks. Extending it to match tenacity's feature set means reimplementing and testing a battle-tested library. |

**Why now is the right time to switch:** The milestone adds per-provider retry configuration (`DatabaseConfig.max_retries`, `DatabaseConfig.backoff_factor`, `DatabaseConfig.timeout`) — this is the natural integration point. Rather than threading these through a custom decorator, use tenacity's parameterized retry factory. The migration is straightforward because tenacity's decorator-based API mirrors the existing pattern.

**Migration pattern — from custom to tenacity:**

```python
# BEFORE (custom decorator, current code):
from biocurator.utils.network import retry

class NCBISearcher:
    @retry(exceptions=(Exception,), max_attempts=3)
    def search(self, criteria):
        ...

# AFTER (tenacity with per-provider config):
from tenacity import retry, stop_after_attempt, wait_exponential, before_sleep_log

def build_provider_retry(config: DatabaseConfig):
    """Factory: creates a tenacity retry decorator from DatabaseConfig settings."""
    return retry(
        stop=stop_after_attempt(config.max_retries),
        wait=wait_exponential(
            multiplier=config.backoff_factor,
            min=config.retry_min_wait,
            max=config.retry_max_wait,
        ),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )

class NCBISearcher:
    @build_provider_retry(config)
    def search(self, criteria):
        ...
```

**Key tenacity features needed for this milestone:**

| Feature | Usage |
|---------|-------|
| `stop_after_attempt(N)` | Replace hardcoded `max_attempts=3` |
| `wait_exponential(multiplier, min, max)` | Replace custom exponential backoff with jitter |
| `before_sleep_log(logger, level)` | Log retry attempts with structured messages |
| `retry_if_exception_type(tuple)` | Only retry on network-related exceptions, not business logic errors |
| `RetryError` | Let retry exhaustion propagate cleanly through the exception hierarchy |
| `tenacity.Retrying.statistics` | Expose retry stats for CLI `status` command (attempts made, elapsed time) |

**What NOT to do:**
- Do NOT apply tenacity's `@retry` as a blanket decorator on `Exception`. Be specific about which exceptions are retryable (network timeouts, HTTP 429/503, connection errors). Business logic errors (HTTP 400, 404) should fail fast.
- Do NOT use tenacity's `stop_after_delay` as primary stop condition — `stop_after_attempt` with per-provider max is more predictable for users.
- Do NOT add `before` or `after` callbacks that log every attempt — use `before_sleep_log` which only logs when a retry is about to happen. This avoids log spam on successful-first-attempt calls.

**Installation:**

```bash
uv add tenacity>=9.1
```

---

### 2. Circuit Breaker — pybreaker v1.4.x

**Verdict: Add pybreaker as a per-provider circuit breaker layer.**

| Aspect | Detail |
|--------|--------|
| **Library** | `pybreaker` >= 1.4.0 |
| **Current version** | 1.4.1 (released 2025-09-21) |
| **Python support** | >= 3.9 (compatible with project's 3.13+) |
| **Monthly downloads** | ~21M |
| **License** | BSD 3-Clause |
| **Confidence** | HIGH |

**Why pybreaker:**

The circuit breaker pattern is distinct from retry. Retry handles transient failures (server busy, network blip). Circuit breaker handles sustained failures (server down for minutes/hours). They compose: retry wraps individual calls, circuit breaker wraps the whole operation.

```mermaid
flowchart LR
    A[CLI Command] --> B[Circuit Breaker]
    B -->|CLOSED / HALF-OPEN| C[Retry Layer<br/>(tenacity)]
    C --> D[HTTP Request]
    D -->|Success| E[Return Result]
    D -->|Failure| C
    C -->|All attempts failed| B
    B -->|Exceeded fail_max| F[OPEN STATE<br/>Fast-fail]
```

**Configuration pattern — per-provider circuit breaker:**

pybreaker instances should live as module-level singletons per provider, keyed by provider name. This gives each provider its own failure tracking.

```python
import pybreaker

# One breaker per provider
ncbi_breaker = pybreaker.CircuitBreaker(
    fail_max=5,              # Open after 5 consecutive failures
    reset_timeout=60,        # Try half-open after 60 seconds
    success_threshold=2,     # Require 2 successes to close
    name="ncbi",
    exclude=[ValueError, TypeError],  # Don't count programming errors
)

uniprot_breaker = pybreaker.CircuitBreaker(
    fail_max=5,
    reset_timeout=60,
    success_threshold=2,
    name="uniprot",
)
```

**How retry and circuit breaker compose in practice:**

```python
class CircuitBreakingSearcher:
    """Wraps a searcher with circuit breaker + retry logic."""

    def __init__(self, inner: DatabaseSearcher, breaker: pybreaker.CircuitBreaker):
        self._inner = inner
        self._breaker = breaker

    def search(self, criteria):
        # Circuit breaker call wraps a tenacity-retried inner call
        return self._breaker.call(self._inner.search, criteria)
```

**Listeners for observability (CLI `status` command):**

```python
class CircuitBreakerLogger(pybreaker.CircuitBreakerListener):
    def state_change(self, cb, old_state, new_state):
        logger.warning(
            "Circuit breaker '%s': %s -> %s",
            cb.name,
            old_state.name if old_state else "initial",
            new_state.name,
        )
```

**Store breaker state for `biocurator status` display:**

```python
def get_breaker_status(breaker: pybreaker.CircuitBreaker) -> dict:
    return {
        "name": breaker.name,
        "state": breaker.current_state,         # 'open', 'half_open', 'closed'
        "fail_counter": breaker.fail_counter,
        "fail_max": breaker.fail_max,
        "reset_timeout": breaker.reset_timeout,
    }
```

**Why NOT aiobreaker or custom implementation:**

| Option | Verdict | Reason |
|--------|---------|--------|
| **pybreaker** | ✅ **Recommended** | 666 stars, 21M monthly downloads, active (released 2025-09), clean API, listener pattern built in, thread-safe. |
| **aiobreaker** | ❌ Not needed | Async-native — biocurator is a synchronous CLI tool. Adds unnecessary complexity. |
| **Custom** | ❌ Not recommended | Circuit breaker state management (closed → open → half-open → closed) is finicky to get right, especially with timeout edge cases and concurrent access. A well-tested library costs less than debugging a custom one. |

**Installation:**

```bash
uv add pybreaker>=1.4
```

---

### 3. Health Checks / Status Probing — Custom Pattern

**Verdict: No library needed. Implement a lightweight `HealthChecker` class using requests.**

**Confidence:** HIGH

**Rationale:** The health check libraries on PyPI (`rest-health`, `pulsecheck-py`, `probirka`, `healthpy`, `pihace`) are all designed for **web frameworks** (FastAPI, Flask, aiohttp, Django) exposing `/health` endpoints. They are not appropriate for a CLI tool that probes *external* services.

Biocurator needs CLI-side probing — make a minimal request to each API and report whether it responds. This is a ~50-line custom class.

**Probe pattern by provider:**

```python
import requests
import time
from dataclasses import dataclass, field
from typing import Callable

@dataclass
class HealthCheckResult:
    provider: str
    status: str          # "ok" | "degraded" | "unreachable"
    response_time_ms: float
    error: str | None = None

class HealthChecker:
    def __init__(self):
        self._probes: list[tuple[str, Callable[[], HealthCheckResult]]] = []

    def add_probe(self, name: str, probe_fn: Callable[[], HealthCheckResult]):
        self._probes.append((name, probe_fn))

    def check_all(self) -> list[HealthCheckResult]:
        return [fn() for _, fn in self._probes]

# NCBI probe — hit the EUtils ESG (Entrez Simple GUI) endpoint
def probe_ncbi() -> HealthCheckResult:
    start = time.monotonic()
    try:
        resp = requests.get(
            "https://eutils.ncbi.nlm.nih.gov/",
            timeout=10,
            headers={"User-Agent": "biocurator/0.2.0"},
        )
        elapsed = (time.monotonic() - start) * 1000
        if resp.status_code == 200:
            return HealthCheckResult("ncbi", "ok", elapsed)
        return HealthCheckResult("ncbi", "degraded", elapsed, f"HTTP {resp.status_code}")
    except requests.ConnectionError:
        elapsed = (time.monotonic() - start) * 1000
        return HealthCheckResult("ncbi", "unreachable", elapsed, "Connection failed")
    except requests.Timeout:
        elapsed = (time.monotonic() - start) * 1000
        return HealthCheckResult("ncbi", "unreachable", elapsed, "Timed out")

# UniProt probe — hit the REST API root
def probe_uniprot() -> HealthCheckResult:
    start = time.monotonic()
    try:
        resp = requests.get(
            "https://rest.uniprot.org/",
            timeout=10,
            headers={"User-Agent": "biocurator/0.2.0"},
        )
        elapsed = (time.monotonic() - start) * 1000
        if resp.status_code == 200:
            return HealthCheckResult("uniprot", "ok", elapsed)
        return HealthCheckResult("uniprot", "degraded", elapsed, f"HTTP {resp.status_code}")
    except requests.ConnectionError:
        elapsed = (time.monotonic() - start) * 1000
        return HealthCheckResult("uniprot", "unreachable", elapsed, "Connection failed")
    except requests.Timeout:
        elapsed = (time.monotonic() - start) * 1000
        return HealthCheckResult("uniprot", "unreachable", elapsed, "Timed out")
```

**Display via Rich (existing dependency):**

```python
from rich.table import Table
from rich.console import Console

def display_health(results: list[HealthCheckResult]):
    table = Table(title="API Health Status")
    table.add_column("Provider", style="bold")
    table.add_column("Status")
    table.add_column("Response", justify="right")
    table.add_column("Error", style="dim")

    icon_map = {"ok": "✅", "degraded": "⚠️", "unreachable": "❌"}
    for r in results:
        table.add_row(
            r.provider,
            f"{icon_map.get(r.status, '❓')} {r.status}",
            f"{r.response_time_ms:.0f}ms",
            r.error or "",
        )
    Console().print(table)
```

**Pre-flight check mode:** Before running a job, optionally run `HealthChecker.check_all()`. If any critical provider is "unreachable", warn the user and abort (or continue, configurable). This maps to requirement **RELIAB-04**.

---

### 4. Checksum Verification — `hashlib` (Python stdlib)

**Verdict: No library needed. Use `hashlib.file_digest()` (Python 3.11+).**

**Confidence:** HIGH

Python 3.11 introduced `hashlib.file_digest(fileobj, "sha256")` which is both standard-library (zero dependencies) and optimized (uses `fileno()` to bypass Python I/O where possible). Since the project requires Python >= 3.13, this is available.

```python
import hashlib
from pathlib import Path

def sha256_file(path: Path) -> str:
    """Compute SHA-256 hex digest of a file using the efficient stdlib method."""
    with open(path, "rb") as f:
        digest = hashlib.file_digest(f, "sha256")
    return digest.hexdigest()

def verify_checksum(path: Path, expected: str) -> bool:
    """Verify a file's SHA-256 checksum matches the expected value."""
    return sha256_file(path) == expected
```

**Why SHA-256 (not MD5, not SHA-512, not BLAKE2):**

| Algorithm | Verdict | Reason |
|-----------|---------|--------|
| **SHA-256** | ✅ **Recommended** | Best balance of security (no known collisions after 20+ years), performance (~500 MB/s on modern CPUs), and ecosystem compatibility. Used by Linux package managers, PyPI, and most scientific data portals. |
| MD5 | ❌ Not for integrity | Cryptographically broken (collisions in seconds on modern hardware). Still used for non-security checksums but not recommended for new code. |
| SHA-512 | ❌ Overkill | 2-3x slower than SHA-256 with no real security benefit for file integrity use. Only needed for FIPS compliance or classified data. |
| BLAKE2 | ❌ Less portable | Faster than SHA-256 but not supported by standard tools (`sha256sum` on Linux, `CertUtil -hashfile` on Windows). Users can't verify independently without Python. |

**When to checksum:**
1. On download (after writing file to disk) — `Exporter` computes SHA-256 immediately
2. On `biocurator files --verify` — read file, compute SHA-256, compare with stored checksum
3. On re-download — if stored checksum doesn't match, file may be corrupted

---

### 5. Manifest Tracking — Custom JSON Schema

**Verdict: No library needed. Simple JSON schema with dataclass or TypedDict.**

**Confidence:** HIGH

Each job run produces a manifest JSON file alongside the downloaded data. The manifest is the source of truth for `biocurator files` and `biocurator files --verify`.

**Manifest schema:**

```python
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import json

@dataclass
class DownloadEntry:
    url: str
    filepath: str           # Relative path from manifest location
    size_bytes: int
    sha256: str
    record_count: int
    timestamp: str          # ISO 8601

@dataclass
class JobManifest:
    manifest_version: str = "1.0"
    job_name: str = ""
    provider: str = ""
    config_file: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    total_records: int = 0
    files: list[DownloadEntry] = field(default_factory=list)

    def to_json(self, path: Path):
        with open(path, "w") as f:
            json.dump(self, f, indent=2, default=lambda o: o.__dict__)

    @classmethod
    def from_json(cls, path: Path) -> "JobManifest":
        with open(path) as f:
            data = json.load(f)
        return cls(**data)
```

**Storage location:** `{outdir}/{job_name}/.biocurator_manifest.json` (hidden file in job output directory).

**Why JSON (not YAML, not SQLite, not TOML):**

| Format | Verdict | Reason |
|--------|---------|--------|
| **JSON** | ✅ **Recommended** | Universally readable, Python `json` module is stdlib, easy for users to inspect. Standard schema validation possible with `jsonschema` if needed. |
| YAML | ❌ More complex | Requires `pyyaml` (already a dependency but not for this purpose). Ambiguities with tags, anchors. |
| TOML | ❌ Not suitable | No built-in Python writer before 3.11, not designed for data records. |
| SQLite | ❌ Overkill | Single-user CLI tool with one manifest per job. No querying needed. |

---

### 6. `DatabaseConfig` Extension — New Fields

The existing `DatabaseConfig` needs new fields to support configurable retry and circuit breaker parameters:

```python
@dataclass
class DatabaseConfig:
    name: str
    base_url: str | None = None
    api_key: str | None = None

    # Existing
    rate_limit: float = 0.3      # Seconds between requests
    batch_size: int = 20
    timeout: int = 30             # Request timeout in seconds

    # NEW — Retry configuration (affects tenacity behavior)
    max_retries: int = 3
    backoff_factor: float = 2.0  # Multiplier for exponential backoff
    retry_min_wait: float = 1.0  # Minimum wait in seconds (tenacity param)
    retry_max_wait: float = 60.0 # Maximum wait in seconds (tenacity param)

    # NEW — Circuit breaker configuration (affects pybreaker behavior)
    circuit_breaker_fail_max: int = 5
    circuit_breaker_reset_timeout: int = 60  # Seconds before half-open
    circuit_breaker_success_threshold: int = 2
```

These fields flow from YAML config → `DatabaseConfig` → retry/circuit breaker factories, completing the **RELIAB-02** requirement.

---

## Summary of Dependency Changes

| Action | Package | Version | Type |
|--------|---------|---------|------|
| **Add** | `tenacity` | `>=9.1` | Production dependency |
| **Add** | `pybreaker` | `>=1.4` | Production dependency |
| **Keep** | `hashlib` | (stdlib) | — |
| **Keep** | `json` | (stdlib) | — |
| **Keep** | `pathlib` | (stdlib) | — |
| **Remove** | Custom `@retry` | — | Replace with tenacity |

**No changes needed to:** `requests`, `biopython`, `typer`, `rich`, `pyyaml`, `pandas`, `numpy`, `pytest`, `pytest-mock`.

## What NOT to Use — Explicit Rejections

| Library | Why Rejected |
|---------|-------------|
| `backoff` (or `python-backoff`) | Original repo archived, fork has 25 stars. Tenacity is the community standard. |
| `aiobreaker` | Async-native, not appropriate for a sync CLI tool. |
| `tenacity.async` features | Project is synchronous. Async retry features would be unused complexity. |
| `httpx` | Would require replacing all `requests` calls. Not worth the churn — the existing `requests` + tenacity + pybreaker covers all HTTP robustness needs. |
| `retry` (the original `retrying` library) | Abandoned since 2016. Tenacity is its spiritual successor. |
| `rest-health`, `pulsecheck-py`, `probirka`, `healthpy` | All designed for web frameworks exposing `/health` endpoints. Not applicable to a CLI tool probing external services. |
| `cryptography` | `hashlib` in stdlib already provides `file_digest()` which is optimized. No need for heavy crypto library for file checksums. |
| `jsonschema` | Manifest schema is simple enough that schema validation overhead (dependency, compile step) isn't justified. If manifests grow complex later, add it. |

## Installation

```bash
# Add production dependencies
uv add 'tenacity>=9.1'
uv add 'pybreaker>=1.4'

# (No dev dependency changes needed)
```

## Sources

- **tenacity**: PyPI v9.1.4 (2026-02-07), 389M monthly downloads, 9K GitHub stars. [PyPI](https://pypi.org/project/tenacity/) | [GitHub](https://github.com/jd/tenacity) — **HIGH confidence**
- **pybreaker**: PyPI v1.4.1 (2025-09-21), 21M monthly downloads, 666 GitHub stars. [PyPI](https://pypi.org/project/pybreaker/) | [GitHub](https://github.com/danielfm/pybreaker) — **HIGH confidence**
- **hashlib.file_digest**: Python 3.11+ stdlib. [Python docs](https://docs.python.org/3/library/hashlib.html#hashlib.file_digest) — **HIGH confidence**
- **backoff status**: Original `litl/backoff` archived. Fork `python-backoff` v2.3.1 (2025-12-18) with 25 stars. [GitHub](https://github.com/python-backoff/backoff) — **MEDIUM confidence**
- **Existing stack**: Verified via `pyproject.toml` and `uv.lock` — **HIGH confidence**
