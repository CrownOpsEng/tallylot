---
title: "Reconciliation Artifacts"
summary: "Durable baseline and drift-analysis artifacts kept under the mirrored reconciliation subtree."
doc_type: reference
audience: both
owner: repo
status: active
---

This folder stores durable reconciliation and oracle comparison artifacts.

## Balance Assertion Artifacts

Runtime balance assertion workflows write these artifacts here:

- `balance_assertions.csv`
- `reconciliation_issues.csv`
- `balance_assertion_summary.json`

`balance_assertions.csv` records matched, drift, missing-side, and timestamp
mismatch rows for one source's balances and source-backed balance evidence.
`reconciliation_issues.csv` stores the corresponding explicit issues, including
duplicate input rows, and `balance_assertion_summary.json` records the artifact
counts for that run.

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
