---
phase: 05-pre-flight-check-integration
plan: 01
subsystem: config
tags: [config, yaml, schema, dataclass]
dependency_graph:
  requires: []
  provides: [CFG-03, STATUS-04]
  affects: [config-schema, config-loader, preflight-check]
tech-stack:
  added: []
  patterns: [dataclass-field-with-default, backward-compatible-yaml-parsing]
key-files:
  created: []
  modified:
    - src/biocurator/config/schema.py
    - src/biocurator/config/loader.py
    - tests/config/test_schema.py
    - tests/config/test_loader.py
decisions:
  - Added preflight_check as bool (not bool | None) with False default for backward compatibility
  - Positioned field after breaker in SearchConfig, parsed from search.preflight_check in YAML
metrics:
  duration: ~3 min
  completed_date: 2026-05-25
---

# Phase 5 Plan 1: Add preflight_check Config Field Summary

**One-liner:** Added `preflight_check` boolean field to `SearchConfig` dataclass with backward-compatible YAML parsing via `ConfigLoader`.

## Objective

Add `preflight_check` boolean field to `SearchConfig` dataclass and YAML parsing in `ConfigLoader`, fully backward compatible. This enables per-job pre-flight health check configuration so users can opt in to automatic provider health probes before job execution.

## Tasks Executed

| # | Task | Type | Commit | Status |
|---|------|------|--------|--------|
| 1 | Add preflight_check field to SearchConfig | auto | `8e3ab4e` | ✅ |
| 2 | Parse preflight_check in ConfigLoader._parse_job() | auto | `4b3c198` | ✅ |
| 3 | Add schema and loader tests for preflight_check | auto | `7a37af7` | ✅ |

## What Was Built

### 1. SearchConfig.preflight_check field (`schema.py`)
- Added `preflight_check: bool = False` to the `SearchConfig` dataclass
- Positioned after the existing `breaker` field at line 124
- Uses plain `bool` type (not `bool | None`) with `False` default — consistent with `sequence_type: str = "nucleotide"` pattern
- No other fields modified

### 2. YAML parsing (`loader.py`)
- Added `preflight_check=search_data.get("preflight_check", False)` to the `SearchConfig(...)` constructor in `_parse_job()`
- Uses same pattern as other optional fields (`search_data.get(...)` with sensible default)
- PyYAML auto-converts `true`/`false` YAML values to Python `True`/`False`
- No validation needed — malformed values naturally parsed by PyYAML

### 3. Tests (4 new, all passing)
- **test_schema.py**: `test_search_config_preflight_check_defaults_false` (default is False), `test_search_config_preflight_check_explicit` (True/False stored)
- **test_loader.py**: `test_preflight_check_parsed_from_yaml` (YAML `true` → Python `True`), `test_preflight_check_defaults_false_when_missing` (backward compat)

## Verification

- **Unit tests**: 186 passed (182 existing + 4 new) — zero regressions
- **Backward compatibility**: `SearchConfig(databases=['ncbi'])` → `preflight_check == False` (default)
- **YAML parsing**: YAML without `preflight_check` key parses as `False`; YAML with `preflight_check: true` parses as `True`

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check

All deliverables verified:
- ✅ `src/biocurator/config/schema.py` — `preflight_check` field at line 124
- ✅ `src/biocurator/config/loader.py` — `preflight_check` parsed at line 69
- ✅ `tests/config/test_schema.py` — 2 new tests added
- ✅ `tests/config/test_loader.py` — 2 new tests added
- ✅ All 186 tests pass (182 existing + 4 new)
- ✅ All 3 commits on main branch

## Decisions Made

- **Plain `bool` not `bool | None`**: Avoids extra `None` sentinel case downstream; `False` default achieves same backward compat
- **Position after `breaker`**: Follows natural grouping — config fields appear in order they were added to the schema
- **No custom deserialization**: PyYAML's native `true`/`false` handling is sufficient, no `from_dict` method needed
