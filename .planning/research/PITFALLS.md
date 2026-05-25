# Domain Pitfalls: Reliability Features for a Bioinformatics CLI Curation Tool

**Domain:** Config-driven CLI for biological sequence curation from NCBI/UniProt
**Researched:** 2026-05-25
**Target milestone:** Reliability improvements (circuit breakers, retry config, checksums, CLI status commands)

---

## Critical Pitfalls

Mistakes that cause silent data loss, broken workflows, or wasted engineering effort.

### Pitfall C1: Circuit Breaker Fights the Retry Mechanism

**What goes wrong:** You add a circuit breaker that counts HTTP 429 (rate limit) or 503 (temporarily unavailable) as "failures." The retry decorator is also configured to retry on these same errors. The circuit breaker opens *after* retries exhaust — meaning every rate-limit burst not only wastes retry attempts but also triggers the circuit breaker, which then blocks *all* subsequent requests (including to other providers) for a recovery period.

**Why it happens:**
- Two independent resilience layers (retry + circuit breaker) with overlapping error classification
- Default circuit breaker configs from web-microservice patterns copied in without adaptation — typical patterns use 5 failures in 60s, which is trivial to hit during an NCBI batch (a single 500-id download over one-at-a-time `efetch` makes 500 calls)
- Both layers catch `requests.RequestException` without distinguishing transient vs persistent failure

**Consequences:**
- A brief NCBI glitch that a simple retry would mask instead trips the breaker, blocking all jobs for the recovery period
- UniProt requests are blocked because the *shared* circuit breaker opened from an NCBI failure
- User sees "NCBI unavailable" for 60+ seconds, retries the job, and exacerbates the problem

**Prevention:**
- **1 circuit breaker per provider**, never shared. NCBI being down should not block UniProt.
- Circuit breaker failure count should track *consecutive* failures *after* retries are exhausted, not raw failures. A failure that retried successfully is not a circuit-worthy event.
- Rate limit (429/403) responses should be excluded from circuit breaker counts — they are signals to slow down, not service failures. Handle them with rate-limit-aware backoff, not circuit opening.
- Configure thresholds generously: minimum 10-20 consecutive *unretryable* failures before opening, with a 30-second recovery timeout. Bio APIs have longer tails than microservice APIs.
- Use the `@retry` decorator as the FIRST line of defense, circuit breaker as the last resort for sustained outages.

**Warning signs:**
- CI tests where circuit breaker tests pass but the breaker never actually opens in real usage
- Users reporting "NCBI is blocked" after single failed runs
- Rate-limit errors (429) appearing in circuit breaker failure logs
- Multiple providers showing as "unavailable" when only one is problematic

**Phase mapping:** Circuit breaker implementation phase. Must be designed alongside retry config, not added as an afterthought.

---

### Pitfall C2: Retry On All Exceptions (Including Non-Recoverable)

**What goes wrong:** The `@retry` decorator currently defaults to `exceptions=(Exception,)` — the broadest possible catch. This retries `AttributeError` (coding bug), `TypeError` (type mismatch), `KeyboardInterrupt` (user wants to stop), and `MemoryError` (OOM). The user waits 3+ retry cycles while the tool repeatedly crashes into the same programming error.

**Why it happens:** Convenience — "(Exception,)" requires no thought. The developer assumes that if an exception reached the retry decorator, it must be network-related.

**Consequences:**
- **KeyboardInterrupt retried:** User presses Ctrl+C to cancel, tool catches it as a generic `Exception` (since `KeyboardInterrupt` inherits from `BaseException`, not `Exception` — actually this case is safe, but only because of Python's inheritance hierarchy, not by design). However, the `@retry` catches `Exception` subclasses only, so `KeyboardInterrupt` passes through — but a `requests.Timeout` wrapping a `KeyboardInterrupt` would not.
- **AttributeError/TypeError masked:** A code bug that raises `AttributeError` gets retried 3 times (with delays) before failing. The user sees a generic "max retries exceeded" error, not the actual bug.
- **Parse errors retried:** NCBI XML schema changes cause `Entrez.read()` to raise `ValueError` — this gets retried 3 times with 1s/2s/4s delays, wasting 7+ seconds before reporting the real problem.
- **MemoryError retried (sort of):** `MemoryError` is a subclass of `Exception` — yes, it would be retried. The tool would fail 3 times as it runs out of memory.

**Prevention:**
- Change the default to catch only `requests.RequestException`, `urllib3.exceptions.HTTPError`, and `IOError` — the retryable network errors.
- Parse errors (`XMLSyntaxError`, `ValueError` from `Entrez.read()`) should never be retried. Separate network retry from parsing into distinct try/except blocks.
- Let `KeyboardInterrupt`, `SystemExit`, `GeneratorExit` (all `BaseException` subclasses) propagate immediately.
- Add an explicit `non_retryable_exceptions` parameter to the `@retry` decorator that immediately re-raises.

**Warning signs:**
- Retry logs showing errors like `AttributeError: 'NoneType' object has no attribute 'read'`
- Users reporting "the tool hangs when I press Ctrl+C"
- CI test for retry decorator that passes a non-retryable exception through

**Phase mapping:** Retry configuration phase. Must be fixed *before* or *concurrently with* adding circuit breakers.

---

### Pitfall C3: Checksum Done Wrong — False Confidence

**What goes wrong:** The tool generates SHA-256 checksums for downloaded files but the verification gives false confidence because:
1. The checksum is computed *while streaming the file to disk* and stored immediately — verifying against the *same* in-memory hash catches nothing if the write was corrupted
2. The checksum is stored *in* the output directory alongside the files — if the disk corrupts the directory, both file and checksum are corrupted together
3. The verification only checks that the manifest *exists* and the file *exists*, not that the checksum actually matches
4. Different export formats get different handling: one format's checksum covers the full file, another's covers only metadata

**Why it happens:**
- Convenience: generating checksum during streaming is "free" (no extra read pass)
- The manifest feels authoritative: "the manifest says these checksums, so data must be good"
- Developers test on their own machine where corruption never happens

**Consequences:**
- **Silent data corruption:** File writes that suffer from buffered-I/O partial writes (rare but possible on full disks or network mounts) are not detected because the checksum was computed from the *write buffer*, not the *final on-disk bytes*
- **Undetected bit-rot:** Both checksum and file degrade on the same physical disk — neither catches the other's corruption
- **False sense of security:** User sees "All checksums verified ✓" but the tool never actually *compared* the stored checksum to a freshly-computed one

**Prevention:**
- **Verify from disk, not from buffer.** Always compute the checksum by re-reading the *completed on-disk file* in a separate pass. This catches buffer-to-disk corruption.
- **Store checksums outside the output directory.** Use `~/.local/share/biocurator/manifests/` or the config directory. This separates the checksum from the data it protects.
  - If you must store in the output directory, also maintain a "tag manifest" (BagIt-style) that checksums the manifest itself. This creates a chain of trust.
- **`--verify` must recompute and compare, not just check existence.** The `biocurator files --verify` command must:
  1. Read the stored checksum from manifest
  2. Open the file and re-compute SHA-256 from scratch
  3. Compare — log MATCH or MISMATCH per file
- **Use a standard format.** Follow BagIt (RFC 8493) `manifest-sha256.txt` format (one `checksum  relative/path` per line). This lets users verify with standard `sha256sum -c` independently of your tool. Do NOT invent your own YAML-based manifest format.
- **Record metadata in the manifest:** algorithm, file size, creation timestamp. This helps debug mismatches (e.g., "file was truncated" vs "file was modified").

**Warning signs:**
- Verifying against a manifest in the same directory as the files (split-brain risk)
- Checksums generated in `__enter__` or stream write handler (before data is flushed to disk)
- `--verify` command that always prints "OK" because it only checks file existence
- No test where a corrupted file is detected by verification

**Phase mapping:** Checksum/manifest implementation phase.

---

### Pitfall C4: Status Command That Gives False Positives/Negatives

**What goes wrong:** The `biocurator status` command probes API availability and reports misleading results:
- **False positive:** The status command sends a lightweight HTTP HEAD to `www.ncbi.nlm.nih.gov` and gets a 200 response — but the actual E-utilities endpoint (`eutils.ncbi.nlm.nih.gov`) is down. User proceeds to run a job that immediately fails.
- **False negative:** The status command does a real ESearch query and gets rate-limited (429). It reports "NCBI: UNAVAILABLE" — but NCBI is fine, the user just needs to wait 1 second.

**Why it happens:**
- Testing connectivity ≠ testing API availability (different hostnames, CDN edge vs application servers)
- Confusing "server responded" with "server is ready to serve your request"
- A single probe point gives binary pass/fail that maps poorly to real API behavior

**Consequences:**
- Users lose trust in the status command after seeing "ALL OK" followed by errors in `run`
- Users avoid legitimate runs because the status command reported a transient rate-limit as "DOWN"
- The status command itself becomes a source of support questions ("why does status say FAIL but my download works?")

**Prevention:**
- **Probe the actual API endpoints, not the homepage.** For NCBI: hit `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/einfo.fcgi` (the lightweight database info endpoint). For UniProt: hit `https://rest.uniprot.org/` or `https://rest.uniprot.org/uniprotkb/search?query=*&size=1`.
- **Use a dedicated status probe that differs from the job request.** Never use ESearch or other rate-limited-budget calls for status checks. `einfo` is designed for this — it consumes virtually no server resources.
- **Report per-endpoint status, not a single "ALL OK."** Show NCBI (search), NCBI (fetch), UniProt (search), UniProt (fetch) independently. A "degraded" state (one endpoint slow) is very different from "down" (all endpoints failing).
- **Include response time, not just pass/fail.** If NCBI search takes 5 seconds but works, the user should know — this predicts slow jobs.
- **Cache status results** for 30-60 seconds. Multiple rapid calls to `biocurator status` should not hammer the APIs.
- **Distinguish "unreachable" from "rate-limited":**
  - HTTP 429 → "NCBI: Rate limited (retry in N seconds)"
  - TCP timeout → "NCBI: Unreachable"
  - DNS failure → "NCBI: DNS resolution failed"
- **If a probe fails, retry once after 2 seconds.** A single connection timeout often resolves.

**Warning signs:**
- Status always says "OK" even when a concurrent download is failing
- Status always says "FAIL" on the first attempt after any idle period
- Status command triggers rate-limit warnings in application logs
- Users say "status works but nothing else does"

**Phase mapping:** CLI status command phase.

---

### Pitfall C5: Manifest File Format That Becomes Unmaintainable

**What goes wrong:** The team defines a custom JSON or YAML manifest format that seems fine initially but becomes painful:
- No standard tool can verify it — users must use `biocurator files --verify` (vendor lock-in)
- Schema evolves (new fields, changed fields) with no versioning — old manifests become unreadable
- Full file paths are stored — renaming output directory breaks all manifests
- Binary/hex encoding style differs across platforms (uppercase vs lowercase, with/without spaces)
- Format is fragile: a single corrupted byte in the manifest makes the entire thing unparseable

**Why it happens:**
- Custom formats feel natural ("we control it, we can extend it")
- BagIt looks complex for a simple use case ("we just need checksums, not a whole packaging standard")
- No upfront consideration of long-term data portability

**Consequences:**
- Users who archive their results cannot verify data integrity 2 years later without the exact same version of the tool
- Manifests in different projects use incompatible formats — no ecosystem tooling
- A future developer has to write migration scripts for every versions of the manifest format
- The "just a simple JSON" format balloons to 5 version-incompatible variants

**Prevention:**
- **Use BagIt (RFC 8493) manifest format.** It is:
  - An open standard (not tool-specific)
  - Verifiable with standard `sha256sum -c` on Linux/macOS, `certutil -hashfile` on Windows
  - Simple: `checksum  relative/path/to/file` one per line, UTF-8, no escaping footguns
  - Extensible (you can add `bag-info.txt` for job metadata alongside the standard manifest)
  - Self-validating with a tag manifest that checksums the metadata files
- **Store checksum algorithm in the filename** (`manifest-sha256.txt`, not `manifest.txt`). This prevents ambiguity about what algorithm was used.
- **Use relative paths from the output directory**, never absolute paths. This makes the output directory relocatable.
- **Record one entry per file per job run.** If a file is regenerated, the manifest gets a new entry with a new timestamp. This enables traceability.
- **Do NOT use YAML for manifests.** YAML is too complex (Tabs vs spaces, encoding issues, anchors/aliases create ambiguity) and has no standard checksum verification tooling. `sha256sum -c` format is the right choice.
- **Document the format.** A README in the output directory explaining the manifest format helps future data recovery.

**Warning signs:**
- Discussion of "our custom manifest format" in planning documents
- YAML manifest files being proposed
- Full absolute paths in manifest examples
- No plan for what happens when a manifest file is partially corrupted

**Phase mapping:** Checksum/manifest implementation phase. Format must be decided before a single checksum is written.

---

### Pitfall C6: Over-Engineering Reliability for a Local CLI Tool

**What goes wrong:** The reliability features (circuit breakers, configurable retry, health checks, manifest verification) are designed as if this were a distributed microservice handling millions of requests per day. The project ships with:
- A stateful circuit breaker daemon with persistence
- Prometheus metrics export
- Redis-backed rate limiting
- A "reliability dashboard" in HTML
- Complex state machine for job lifecycle

**Why it happens:**
- Developers bring patterns from cloud-native/microservice work without considering the scale and context
- Reliability feels like a "serious engineering" problem, inviting over-engineering
- The project's existing architecture (providers, registry, streaming pipeline) already feels "enterprise" — it's tempting to match that tone for reliability

**Consequences:**
- 80% of the reliability code exists to handle scenarios that will never happen (multiple concurrent users, distributed failures, server overload)
- Maintenance burden outweighs the reliability benefit
- New contributors are intimidated by the reliability infrastructure
- Users run a single command on their laptop; the circuit breaker state doesn't need to survive a crash
- The simple case (a `time.sleep()` after rate limit) is invisible under 5 layers of abstraction

**Prevention:**
- **The circuit breaker can be in-memory only.** There is no need to persist circuit state across process restarts — if the user reruns the tool, the previous session's circuit state is obsolete anyway. A Python `datetime` + counter is sufficient.
- **Retry configuration should be a few numbers in YAML, not a DSL.** `max_attempts: 5`, `backoff_factor: 2.0`, `timeout: 30`. Not a full condition system with "if error type X then retry with strategy Y."
- **Health checks should be a single HTTP GET to lightweight endpoints.** Not a multi-stage diagnostic with dependency graph traversal.
- **Manifests should be simple flat files in BagIt format.** Not a SQLite database or a JSON API.
- **Before adding any reliability feature, ask: "Does this help a user running one job on one laptop?"** If the answer involves "distributed," "multi-tenant," or "production SLA," it's the wrong answer.
- **Set an explicit scope boundary:** "All reliability state lives in this Python process and dies when the process exits."
- **Prefer `time.sleep()` over complex backoff libraries** for a CLI tool. The difference between exponential backoff with jitter and simple `sleep(delay * attempt)` is negligible for job-level retries.

**Warning signs:**
- PR descriptions mentioning "production-grade" for local tool features
- Adding Redis, SQLite, or file-based persistence for transient state
- Circuit breaker configuration with more than 4 parameters
- A `reliability/` subpackage in the source tree before the `run` command works reliably
- Discussions about "metrics export" or "grafana dashboards"

**Phase mapping:** All reliability phases. This is a design constraint, not a single feature.

---

### Pitfall C7: Breaking Existing YAML Config When Adding New Fields

**What goes wrong:** Adding reliability configuration (retry settings, circuit breaker thresholds, health check URLs) to the YAML schema breaks existing configs. Common breakage patterns:
- A required field is added where no default exists
- A field is renamed (`max_attempts` → `max_retries`) without backward compat
- The type of an existing field changes (e.g., single value → list of values)
- Default behavior changes silently (e.g., retry was always on, now it defaults to off)

**Why it happens:**
- Config is validated at load time with strict schema checking
- New fields are conceptually "optional" but implemented as "required" at validation time
- Dataclasses make it easy to add fields but hard to express "deprecated but still accepted"

**Consequences:**
- Existing YAML configs that worked with v0.2.0 fail to load in v0.3.0
- Users see `InvalidConfigError` with messages about missing `search.retry.max_attempts`
- Workflows break silently because a field default changed behavior
- The team has to support "config version" migration logic — a path they never wanted to go down

**Prevention:**
- **Every new config field must have a `None` default.** Only `email` and `databases` should be truly required. New fields like `search.retry.max_attempts` must be fully optional.
- **When renaming, accept both names for one release cycle.** Load `max_attempts` if `max_retries` is absent. Log a deprecation warning if the old name is used.
- **Never change field types.** If a field was `int`, it stays `int`. If you need more expressiveness, add a new field.
- **Use Pydantic for config validation, not raw dataclasses.** Pydantic v2+ has explicit support for:
  - `Field(None)` for optional-with-default
  - `Alias` for backward-compatible field names
  - `model_config` for extra field handling
  - If Pydantic is too heavy, at minimum validate with explicit `is None` checks (not truthiness) and document defaults clearly.
- **Test an old v0.2.0 config against the v0.3.0 loader.** This should be an automated test that lives forever, catching accidental breakage.
- **Document change behavior.** In release notes and changelog, every config change gets: "Old behavior: X, New behavior: Y, Config migration: Z."

**Warning signs:**
- Adding a field without a default that would cause `InvalidConfigError`
- "I'll just rename this field, nobody is using it yet"
- Config schema changes are in a PR without testing against the previous version's example config
- `Optional[Type]` fields that raise `ValidationError` when `None` is provided

**Phase mapping:** Config schema updates in ANY phase. Every phase that touches config must treat backward compat as a first-class requirement.

---

### Pitfall C8: NCBI Entrez API Specific Pitfalls

**What goes wrong:** The tool interacts with NCBI's E-utilities API in ways that work during testing but fail in real usage:

| Pitfall | Symptom | Root Cause |
|---------|---------|------------|
| WebEnv expiration | `efetch` fails after several minutes of filtering | WebEnv/query_key expire after 8 hours of inactivity, but more importantly, the history server has finite storage and entries can be evicted under load |
| retmax hard cap | Only 10,000 records retrieved despite 50,000 available | NCBI ESearch `retmax` is capped at 10,000 per call. Need to use `retstart` + `WebEnv` to paginate |
| XML schema changes | `Entrez.read()` raises `ValueError` with cryptic XML parse error | NCBI occasionally changes XML response format. No version pinning in the API call |
| API key + email mismatch | Random 401 errors | Registered API key uses one email, tool sends another. NCBI validates email matches the API key registration |
| Rate limit per key (not per IP) | Unexpected rate limiting on shared networks | Without API key: 3 req/s shared across the IP. With API key: 10 req/s per key, not per IP. Multiple users behind NAT share the 3 req/s quota |
| Bio.Entrez internal sleep | Rate limiting persists even with low concurrency | `Bio.Entrez` implements its own rate limiting via `time.sleep()` after each call. The tool's own `rate_limit` plus Bio.Entrez's internal throttle interact unpredictably |
| EPost + WebEnv batch size | Random "Request too large" errors | EPost and EFetch have undocumented batch size limits. Batches over ~500 IDs can fail |

**Why it happens:**
- NCBI's E-utilities documentation is comprehensive but vast — easy to miss critical parameters
- Bio.Entrez abstracts away many details, so developers assume it "just works"
- Test configs use small datasets (5-10 records) that never hit pagination, expiration, or batch limits
- The NCBI API evolves periodically (schema tweaks, new parameters) without versioned endpoints

**Prevention:**
- **Pagination loop, not single fetch.** Use `retstart` + `retmax` + `WebEnv` to paginate through large result sets. Stop only when `retstart + retmax >= total_count` in search results.
- **Batch downloads, not one-at-a-time.** The current code fetches one record per `efetch` call. Batch with `retmax=500` and `id` list (or WebEnv + query_key with `retmax`). This reduces API calls by 500x and eliminates most rate-limit problems.
- **WebEnv with timeout recovery.** If `efetch` with WebEnv fails, fall back to direct ID-based fetch. WebEnv is a performance optimization, not a requirement.
- **Separate network errors from parse errors.** `@retry` should retry network errors (timeout, connection reset, 429), not parse errors (XML format changes, unexpected field types). Parse errors should fail fast with an informative message.
- **Validate email + API key match at startup.** Make a single `einfo` call when the tool starts. If it fails with a 401 or "invalid API key" error, warn the user immediately.
- **Set Entrez.tool explicitly.** `Entrez.tool = "biocurator/0.3.0"` helps NCBI track usage and helps you debug if your tool is causing issues.
- **Document NCBI rate limit behavior.** Make it clear in the user-facing docs: without API key, max 3 req/s; with API key, max 10 req/s. And that Bio.Entrez enforces this internally, so the tool's `rate_limit` config is an *additional* delay on top of that.

**Warning signs:**
- Test datasets with < 20 records (never exercise pagination)
- `Entrez.read()` errors in production that never appear in tests
- Users reporting "only 10,000 results" when their search matches more
- Intermittent "HTTP 429" errors even with low concurrency
- No tests for `retstart`/`WebEnv` parameters

**Phase mapping:** NCBI searcher reliability fixes (RELIAB-01/02) and optionally a dedicated API compatibility audit phase.

---

### Pitfall C9: Over-Mocking in Tests — Tests Pass, Real Behavior Fails

**What goes wrong:** The reliability features (circuit breaker, retry, health checks, checksum verification) are tested with heavy mocking. Tests verify that:
1. The circuit breaker *would* open if a mock returned the right error
2. The retry decorator *would* retry if a mock raised the right exception
3. Verification *would* detect corruption if a mock returned a different checksum

But in production:
1. The circuit breaker never opens because the real error types don't match what the mock returned
2. The retry retries non-retryable errors (because the test never verified narrow exception handling)
3. Verification passes on corrupted files because the checksum was computed from the write buffer, not the on-disk file

**Why it happens:**
- Mocking makes tests fast (no network calls), deterministic, and easy to write
- The `MagicMock` pattern in the current codebase encourages "mock at the highest level possible"
- Tests look green and CI passes — the team ships with confidence
- The gap between mocked behavior and real behavior is invisible until users hit it

**Consequences:**
- Reliability features that have never actually been tested against real conditions
- A false sense of security: the test suite says "verified" but the actual behavior is untested
- Debugging sessions where a developer spends hours before realizing "the circuit breaker doesn't actually work in this scenario"
- The game of "whack-a-mock": every real-world failure reveals a new test gap that gets patched with another mock

**Prevention:**
- **Use contract tests, not implementation mocks.** Instead of mocking `requests.get` and verifying the circuit breaker handles a `MockException`, inject a *real* HTTP server that returns specific status codes. Use `responses` library, `pytest-httpserver`, or `VCR.py` to record/replay real API responses.
- **Test the circuit breaker end-to-end:** Configure a local HTTP server that fails N times, then succeeds. Verify the breaker opens, the tool stops calling, the recovery happens, and the tool resumes.
- **Test retry with an actual flaky server:** Return 503 for the first 2 calls, 200 on the 3rd. Verify exactly 3 calls were made with correct backoff intervals.
- **Test checksum verification with actual corrupted files:** Write a valid file, compute its checksum, corrupt 1 byte, re-run verification. Assert MISMATCH. Then verify *both* detection and correct error message.
- **Test status with a mock server that returns specific status codes:** 200 (OK), 429 (rate-limited), 503 (down), connection refused (unreachable). Verify the correct human-readable message for each.
- **Minimal mocking policy:** Mock at the I/O boundary (HTTP responses, filesystem) but test the logic through those mocks with real types, not `MagicMock`. If the circuit breaker takes a `requests.Response`, construct one with the real `Response` class, not `MagicMock(status_code=429)`.
- **One integration smoke test with real API calls.** Run `einfo` against real NCBI or a documented test endpoint. Run once per week or on release. This catches API contract drift that mocks would never detect.

**Warning signs:**
- `MagicMock` used everywhere with no real object construction
- Circuit breaker test: mocks the function being called, then mocks the error, then asserts the breaker is open (no actual HTTP involved)
- Checksum test: writes a file and immediately compares checksum without verifying the comparison logic
- Retry test: uses a mock function that raises `Exception` on first call, not the actual exception types from `requests`
- No test that connects to a real (or realistically simulated) network endpoint

**Phase mapping:** Testing for ALL reliability features. Enforce testing standards as part of the definition of done for each reliability feature.

---

### Pitfall C10: Silent Error Swallowing Masks All Reliability Improvements

**What goes wrong:** The team invests in circuit breakers, retry configuration, and checksum verification. But the underlying problem — `except Exception: logger.warning(...); return []` in every searcher method — remains. Every reliability feature is undermined by the error swallowing:
- Circuit breaker opens → great, requests are blocked. But the search method catches the breaker's exception, logs a warning, and returns `[]`. The user sees "0 results found" with no indication the circuit breaker activated.
- Retry exhausts → requests still fail. The retry's last exception is caught by the swallowing handler. The user never sees the "max retries exceeded" error.
- Checksum verification fails → handler catches the exception, logs a warning, and reports "verification skipped." The user sees "All files OK" despite corrupted data.

**Why it happens:** The error swallowing was added as a "make it work" quick fix (CONCERNS.md, HIGH priority). It became the default pattern throughout the searchers. New reliability features are layered on top without removing the underlying swallow.

**Consequences:**
- All reliability work is invisible to the user — findings, warnings, and errors are all consumed by the same `except Exception` handler
- The tool becomes a "black hole" for errors: inputs go in, outputs come out (or don't), and the user has no insight into what happened
- Debugging requires reading log files at `DEBUG` level
- Users cannot distinguish between "no results found" (legitimate) and "search failed" (error condition)

**Prevention:**
- **Remove ALL `except Exception: return []` blocks before adding any new reliability features.** This is the prerequisite for all other reliability work. Without this, adding circuit breakers or retry config is cosmetic.
- **Replace with a clear error classification:**
  - `DatabaseSearchError` for API failures (server down, rate-limited, auth error)
  - `DownloadError` for per-record failures (individual entries that fail to download)
  - Let these propagate to the `run_job` level where the CLI can display them properly
- **Track per-phase error counts.** In `Biocurator.run_job()`, count search failures, metadata fetch failures, and download failures separately. Display a summary: "Completed: 450/500 sequences (50 failed: 48 download errors, 2 rate-limited)"
- **Make the CLI exit code meaningful.** Exit 1 if any job had any error. Exit 2 if all jobs failed. Exit 0 only if all jobs succeeded zero errors.

**Warning signs:**
- Existing CONCERNS.md marks this as HIGH priority — it's already identified
- Adding reliability features without touching the swallowing handlers
- Test suite that tests circuit breakers but uses `MagicMock` searchers that never exercise the swallowing path

**Phase mapping:** RELIAB-01 (fix silent error swallowing). This must be the FIRST reliability task, implemented before circuit breakers (RELIAB-03) or retry config (RELIAB-02).

---

### Pitfall C11: Truthiness Checks on Numeric Config Values

**What goes wrong:** New numeric config fields (e.g., `circuit_breaker.failure_threshold`, `retry.max_attempts`, `checksum.verify_on_run`) use Python truthiness checks like `if config.failure_threshold:` instead of `if config.failure_threshold is not None:`. A value of 0 (which is valid for "no retries" or "no failure limit") is silently treated as "not configured."

**Why it happens:** This bug already exists in the codebase for `min_length`/`max_length` (CONCERNS.md, MEDIUM truthiness check on `min_length`/`max_length`). The same pattern will naturally be repeated when adding new numeric fields.

**Warning signs:**
- New config dataclass fields added with `int | None` type
- `if config.some_field:` used in implementation code (instead of `is not None`)
- Test with value=0 is missing

**Prevention:**
- Always use `is not None` for numeric config fields.
- Add explicit test cases for value=0 for every numeric config field.
- Audit existing code for truthiness checks — the `min_length`/`max_length` bug is a known pattern that will propagate.

**Phase mapping:** Every phase that adds new config fields.

---

## Moderate Pitfalls

### Pitfall M1: Logging Redacts Useful Information

**What goes wrong:** The log redaction filter (`_SensitiveFilter`) redacts entire log messages containing the words "key," "token," "secret," or "password." When a circuit breaker opens because of a "query_key" WebEnv parameter issue, or when a "key" is not found in a response, the entire error message is redacted. Debugging becomes impossible.

**Prevention:** Use targeted regex patterns for API key formats instead of keyword-based redaction. Log the *type* of sensitive information without the value (e.g., `"API key [REDACTED (prefix: ncbi_***)]"` instead of blanking the whole message).

**Phase mapping:** Logging improvements alongside reliability features.

### Pitfall M2: Circuit Breaker State Never Resets Between Runs

**What goes wrong:** The circuit breaker state (open/closed/half-open, failure count) is in-memory only. If the tool processes a job, opens the circuit breaker for NCBI, then the user runs another job for a different organism, the circuit breaker is still open. The user has to wait for the recovery timeout or restart the tool.

**Prevention:** This is actually acceptable behavior for an in-memory circuit breaker — the state is transient and doesn't need to persist. But the *recovery timeout* should be short enough (15-30 seconds) that the user doesn't notice. Document this behavior: "If a provider becomes unavailable, subsequent jobs for that provider are blocked for 30 seconds."

### Pitfall M3: Health Check Consumes Rate Limit Budget

**What goes wrong:** The `biocurator status` command makes real API calls to verify availability. If run frequently (e.g., in a CI script before each job), it consumes the user's NCBI rate limit budget, slowing down actual jobs.

**Prevention:** Status checks should use the most lightweight endpoint possible (`einfo` for NCBI, root GET for UniProt). Cache results for 60 seconds. Rate limit the status command itself (max once per 10 seconds). Document the rate limit impact.

### Pitfall M4: Manifests Grow Without Bound

**What goes wrong:** Every job run creates a new manifest entry. After hundreds of curation runs, the output directory contains dozens of manifest files with no clear relationship to the data files. Finding the "current" manifest becomes impossible.

**Prevention:** Name manifest files with job name and timestamp: `manifest-sha256_{job_name}_{timestamp}.txt`. Keep only the latest N manifests (configurable). Or use the BagIt approach: one `manifest-sha256.txt` per output directory that is *updated* on each successful run (with old entries retained for traceability).

### Pitfall M5: Race Condition Between Retry and Circuit Breaker

**What goes wrong:** The retry decorator and circuit breaker both operate at the provider layer. If a request fails:
1. Retry catches the exception, sleeps, retries (3 times)
2. After retries exhaust, the circuit breaker sees the failure
3. But the circuit breaker counted the *first* failure, not the *last* one — so 5 consecutive batches with retries mean 15 raw failures → circuit opens prematurely

**Prevention:** Design the architecture so that the circuit breaker wraps the retry decorator (sees only one "failure" per batch after retries are exhausted), not the other way around. The chain should be: `request → circuit breaker → retry loop → actual HTTP call`. The circuit breaker tracks only consecutive *unrecovered* failures.

---

## Minor Pitfalls

### Pitfall m1: Hardcoded Test Email Committed to Config

The `config.yaml` contains a real email (`jegsamson.dev@gmail.com`). If NCBI blocks this email (due to policy violations from testing), all users of the committed config are blocked.

**Fix:** Use `your@email.com` placeholder. Document that users must provide their own email.

### Pitfall m2: Entrez Tool Name Not Set

The code sets `Entrez.email` but not `Entrez.tool`. NCBI uses the `tool` parameter to track usage patterns. Without it, all traffic appears as "Biopython" (the default). If your tool triggers rate limiting, NCBI has no way to tell it's a distinct application.

**Fix:** Set `Entrez.tool = "biocurator/0.3.0"` during searcher initialization.

### Pitfall m3: Retry on Parsing Failures Masks API Schema Changes

NCBI/UniProt occasionally change their response formats. The `@retry` decorator on `_safe_entrez_call` retries parse errors from `Entrez.read()`. This means a format change that should fail fast instead retries 3 times (6-14 seconds) before the user sees an error.

**Fix:** Split the `_safe_entrez_call` into two phases: (1) network fetch with retry, (2) parse without retry.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| **RELIAB-01: Fix error swallowing** | Removing `except Exception` blocks reveals hidden error paths (tests pass because exceptions were swallowed) | Add `pytest.raises` tests for every error scenario *before* removing the swallowers. Fix tests first. |
| **RELIAB-02: Configurable retry** | Adding per-provider retry settings to `DatabaseConfig` without backward compatibility | All new fields must be `Optional` with `None = use default`. Test with old configs. |
| **RELIAB-03: Circuit breaker** | Shared circuit breaker across providers; circuit fights with retry | One breaker per provider. Circuit breaker wraps retry, not vice versa. |
| **RELIAB-04: Health check** | Status command hits production APIs and consumes rate limit budget | Use `einfo` (lightweight). Cache results. Document budget impact. |
| **CLI-01: status command** | Single pass/fail for all endpoints when reality is more nuanced | Per-endpoint status with "degraded" state. Include response times. |
| **CLI-02/03: jobs/files commands** | Custom manifest format that locks users into the tool | BagIt `manifest-sha256.txt` format. Verifiable with `sha256sum -c`. |
| **TEST-01/02/03: Checksums** | Checksum computed during stream write (catches nothing) | Re-read file from disk for checksum. Store outside output directory. |
| **Config schema updates** | Breaking existing YAML configs with new required fields | Every new field gets `None` default. Test old configs in CI. |
| **Testing reliability features** | Over-mocking: tests pass, real circuit breaker doesn't work | Contract tests with real HTTP responses (responses/VCR.py). One real API smoke test. |

---

## Sources

- **CONCERNS.md** — Existing codebase analysis (HIGH: silent error swallowing, MEDIUM: retry catches all Exception, MEDIUM: truthiness checks)
- **NCBI E-utilities Documentation** — https://www.ncbi.nlm.nih.gov/books/NBK25501/ — Usage guidelines, WebEnv, rate limits
- **Biopython Entrez Tutorial** — https://biopython.org/docs/dev/Tutorial/chapter_entrez.html — Bio.Entrez rate limiting, API key support
- **NCBI Usage Guidelines** — https://www.ncbi.nlm.nih.gov/books/NBK25497/ — Rate limits (3 req/s without key, 10 req/s with key)
- **Bio.Entrez source** — https://github.com/biopython/biopython/blob/master/Bio/Entrez/__init__.py — Internal rate limiting implementation
- **BagIt RFC 8493** — https://www.rfc-editor.org/rfc/rfc8493 — Standard manifest format for digital preservation
- **AWS Circuit Breaker Pattern** — https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/circuit-breaker.html — Standard circuit breaker pattern reference
- **Pytest mocking best practices** — https://realpython.com/python-cli-testing/ — Techniques for testing CLI apps without over-mocking
- **Easy-Entrez API** — https://easy-entrez.readthedocs.io/en/latest/usage.html — Reference for API key and rate limit handling patterns
- **Network reliability patterns** — https://learn.microsoft.com/en-us/azure/architecture/patterns/circuit-breaker — Circuit breaker + retry interaction guidance
