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

- `balance_inspect.csv`
- `balance_inspect_summary.json`
- `balance_assertions.csv`
- `reconciliation_issues.csv`
- `balance_check_summary.csv`
- `balance_reconciliation_summary.json`
- `balance_reconciliation_blockers.csv`
- `cross_source_assertions.csv`
- `cross_source_issues.csv`
- `cross_source_summary.json`

`balance_inspect.csv` records per-source input mode, snapshot origin, target
and snapshot counts, reference counts, readiness, and date ranges.
`balance_inspect_summary.json` reports counts by inspect status, cross-source
readiness, input mode, and snapshot origin. `balance_assertions.csv` records
matched, drift, missing-side, and observation gap rows for one source's
balance targets plus the selected reference kind. `reconciliation_issues.csv`
stores the corresponding explicit issues, including duplicate or conflicting
reference rows. `balance_check_summary.csv` records per-source resolution
mode, check status, date ranges, and selected-reference-kind counts.
`balance_reconciliation_summary.json` reports the latest clean, latest
resolved-reference, and latest observed dates across the selected sources, and
`balance_reconciliation_blockers.csv` breaks blockers down by source and
reason.

These workflows read assembled source datasets from
`working/normalized/sources/`. Each source subdirectory there is the
reconciliation input for one assembled source.

When compatible location inventory is available across sources,
`cross_source_assertions.csv`, `cross_source_issues.csv`, and
`cross_source_summary.json` record the additive corroboration sidecars emitted
by `reconciliation balances check` over the assembled source datasets. These
sidecars improve confidence across sources, but they do not replace the
source-local balance assertion outputs.

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
