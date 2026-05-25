---
status: partial
phase: 05-pre-flight-check-integration
source: [05-VERIFICATION.md]
started: 2026-05-26T00:00:00Z
updated: 2026-05-26T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Live API Smoke Test

**Test:** `uv run biocurator run config.yaml --check` with a real YAML config targeting NCBI and/or UniProt

**expected:** 
- "Pre-flight Health Check" Rich table renders with actual provider statuses (UP/DOWN), real response times (in ms), and current breaker states
- All providers UP → "All providers reachable. Proceeding with job execution." → job runs
- Any provider DOWN → warning message + "Proceed anyway?" interactive prompt
- `--no-check` skips the table entirely
- Table styling matches `biocurator status` output (same columns, colors, header style)

**result:** [pending]

## Summary

total: 1
passed: 0
issues: 0
pending: 1
skipped: 0
blocked: 0

## Gaps
