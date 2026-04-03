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
- lightweight helper scripts for baseline checks, raw-source manifests, overlap screening, and verification comparison
- repo-local AI skills under `07_skills/` for source intake, normalization exceptions, and round verification

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
4. profile one raw source at a time
5. normalize into canonical events and balances
6. stage and overlap-screen one CoinTracking candidate at a time
7. import one source at a time into CoinTracking
8. capture fresh verification exports after each round
9. stop on unexplained drift and close out at `2025-12-31`

## Testing

Run the full script test suite with:

```bash
python3 -m unittest discover -s tests -v
```

The suite is structured as:

- `tests/unit/` for helper-level behavior
- `tests/e2e/` for CLI execution against real script entrypoints
- `tests/support/` for shared test harness utilities

## Repo intent

This is not a general tax engine. It is a controlled evidence and verification workspace for a one-time historical reconciliation and closeout.
