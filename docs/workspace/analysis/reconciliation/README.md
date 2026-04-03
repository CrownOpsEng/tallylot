---
title: "Reconciliation Artifacts"
summary: "Durable baseline and drift-analysis artifacts kept under the mirrored reconciliation subtree."
doc_type: reference
audience: both
owner: repo
status: active
---

This folder stores durable reconciliation and oracle comparison artifacts.

## Balance Reconciliation Artifacts

Runtime balance reconciliation workflows write these artifacts here:

- `balance_assertions.csv`
- `reconciliation_issues.csv`
- `balance_assertion_summary.json`
- `balance_coverage.csv`
- `balance_coverage_summary.json`
- `balance_check_summary.csv`
- `balance_reconciliation_summary.json`
- `balance_reconciliation_blockers.csv`

`balance_assertions.csv` records matched, drift, missing-side, and timestamp
mismatch rows for one source's balances and source-backed balance evidence.
`reconciliation_issues.csv` stores the corresponding explicit issues, including
duplicate input rows, and `balance_assertion_summary.json` records the artifact
counts for that run. `balance_coverage.csv` and
`balance_coverage_summary.json` describe whether each source is comparable yet.
`balance_check_summary.csv` records per-source check status and date ranges.
`balance_reconciliation_summary.json` reports the latest clean and observed
dates across the selected sources, and `balance_reconciliation_blockers.csv`
breaks blockers down by source and reason.

## Oracle Baseline Package

The dev-only CoinTracking baseline workflow writes these comparison artifacts:

- `baseline_asset_snapshot.csv`
- `baseline_exchange_reconciliation.csv`
- `baseline_negative_balances.csv`
- `baseline_source_activity.csv`
- `baseline_cad_flow_by_type.csv`
- `baseline_cad_balance_by_exchange.csv`
- `baseline_summary.json`

Notes:

- `baseline_exchange_reconciliation.csv` is an internal cross-check between `Current Balance` and `Balance by Exchange`.
- It does not prove that each external exchange or wallet was fully synced to the same cutoff.
- `baseline_source_activity.csv` records the first and last baseline transaction timestamp seen for each source plus whether that source still has balances in `Balance by Exchange`.

Use the light verification export set first. Reach for Roll Forward or
Double-entry only when the simple reports cannot explain a mismatch.
