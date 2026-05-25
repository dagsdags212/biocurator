---
phase: 03
slug: checksums-manifests
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-25
---

# Phase 03 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.4.1 |
| **Config file** | pyproject.toml (no pytest.ini, no conftest.py) |
| **Quick run command** | `python3 -m pytest tests/core/test_exporter.py tests/core/test_verifier.py -x -v` |
| **Full suite command** | `python3 -m pytest tests/ -x -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m pytest tests/core/test_exporter.py tests/core/test_verifier.py -x -v`
- **After every plan wave:** Run `python3 -m pytest tests/ -x -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | DI-01 | N/A | N/A | unit | `pytest tests/core/test_exporter.py::test_sha256_fasta_streaming -x` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | DI-01 | N/A | N/A | unit | `pytest tests/core/test_exporter.py::test_sha256_csv_streaming -x` | ❌ W0 | ⬜ pending |
| 03-01-03 | 01 | 1 | DI-01 | N/A | N/A | unit | `pytest tests/core/test_exporter.py::test_sha256_json_streaming -x` | ❌ W0 | ⬜ pending |
| 03-02-01 | 02 | 2 | DI-02 | N/A | N/A | integration | `pytest tests/core/test_exporter.py::test_manifest_written_to_outdir -x` | ❌ W0 | ⬜ pending |
| 03-02-02 | 02 | 2 | DI-02 | N/A | N/A | integration | `pytest tests/core/test_exporter.py::test_sha256sum_companion_file -x` | ❌ W0 | ⬜ pending |
| 03-02-03 | 02 | 2 | DI-03 | N/A | N/A | integration | `pytest tests/core/test_exporter.py::test_manifest_contains_config_snapshot -x` | ❌ W0 | ⬜ pending |
| 03-02-04 | 02 | 2 | DI-03 | N/A | N/A | integration | `pytest tests/core/test_exporter.py::test_manifest_record_counts -x` | ❌ W0 | ⬜ pending |
| 03-03-01 | 03 | 3 | DI-04 | N/A | N/A | unit | `pytest tests/core/test_verifier.py::test_verify_all_match -x` | ❌ W0 | ⬜ pending |
| 03-03-02 | 03 | 3 | DI-04 | N/A | N/A | unit | `pytest tests/core/test_verifier.py::test_verify_corrupted_detected -x` | ❌ W0 | ⬜ pending |
| 03-03-03 | 03 | 3 | DI-04 | N/A | N/A | unit | `pytest tests/core/test_verifier.py::test_verify_file_missing -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/core/test_exporter.py` — stubs for DI-01 (all three format hashing), DI-02 (manifest writing), DI-03 (config snapshot + record counts)
- [ ] `tests/core/test_verifier.py` — stubs for DI-04 (roundtrip verify: ok, corrupted, missing)
- [ ] `tests/core/test_streaming_curation.py` — MODIFY existing test to assert manifest is produced and checksums are present in curator.run_job() output

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| sha256sum -c works on manifest-sha256.txt | DI-02 | Requires GNU `sha256sum` command; platform-specific (macOS uses `shasum -a 256 -c`) | `cd <outdir> && sha256sum -c manifest-sha256.txt` |
| CSV checksum is reproducible across runs | DI-01 | pandas to_csv determinism tested locally; cross-version verification is manual | Run same export twice, compare generated checksums |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
