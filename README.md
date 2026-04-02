# Crypto Ledger Reconciliation Workspace

This repo is a bounded working package for repairing and extending a CoinTracking.info ledger through `2025-12-31` in a way that supports CRA-aligned Canadian tax reporting.

## Canonical baseline

- source folder: `01_raw_exports/cointracking/2023-08-05_full_export/`
- authoritative cutoff from Trade Table: `2023-08-05 08:34:04`
- delta window starts strictly after that timestamp unless a newer baseline is intentionally adopted

## What this package includes

- the canonical CoinTracking full export and manifest
- a documented baseline validation package
- a populated issue log for known baseline exceptions
- an active source inventory and structured round log
- a universal source-intake pipeline for profiling, canonical normalization, CoinTracking rendering, and reconciliation
- shared inspection, archive handling, routing, overlap, and orchestration modules used across intake, profiling, normalization, staging, and verification
- lightweight helper scripts for baseline checks, raw-source manifests, intake sorting, overlap screening, fixture scaffolding, golden refresh, and verification comparison
- repo-local AI skills under `07_skills/` for source intake, adapter authoring, normalization exceptions, round verification, and wallet inventory

## Start here

- `00_docs/CANADIAN_CRYPTOCURRENCY_TAXATION_GUIDE.md`
- `00_docs/TAX_REFERENCE_MAP.md`
- `00_docs/OPERATIONS_QUICKSTART.md`
- `00_docs/MOP.md`
- `00_docs/BASELINE_VALIDATION.md`
- `00_docs/NEXT_PHASE_EXECUTION_PLAN.md`
- `00_docs/PROJECT_STATE.md`
- `03_analysis/issues/issue_log.csv`
- `03_analysis/issues/source_inventory.csv`
- `05_outputs/logs/round_log.csv`

## Core workflow

1. validate and lock the baseline
2. resolve or document baseline exceptions with evidence
3. inventory post-cutoff sources
4. sort mixed dumps into canonical historical capture folders and archive bundles
   The intake report also consolidates fully redundant package copies when one bundle is a strict superset of another.
5. profile one raw source capture at a time
6. normalize into canonical events and balances
7. stage and overlap-screen one CoinTracking candidate at a time
8. import one source at a time into CoinTracking
9. capture fresh verification exports after each round
10. stop on unexplained drift and close out at `2025-12-31`

## Testing

Run the full script test suite with:

```bash
python3 -m pytest
```

The suite is structured as:

- `tests/adapters/` for adapter-boundary and adapter-pack expectations
- `tests/pipeline/` for orchestration and intake coverage
- `tests/unit/` for helper-level behavior
- `tests/e2e/` for CLI execution against real script entrypoints
- `tests/support/` for shared test harness utilities

## Repo intent

This is not a general tax engine. It is a controlled evidence and verification workspace for a one-time historical reconciliation and closeout.
