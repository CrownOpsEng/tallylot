# Reconciliation Artifacts

This folder stores durable baseline and drift-analysis artifacts.

Current baseline package:

- `baseline_asset_snapshot.csv`
- `baseline_exchange_reconciliation.csv`
- `baseline_negative_balances.csv`
- `baseline_source_activity.csv`
- `baseline_cad_flow_by_type.csv`
- `baseline_cad_balance_by_exchange.csv`
- `baseline_summary.json`

Notes:

- `baseline_exchange_reconciliation.csv` is an internal portfolio-tracker cross-check between `Current Balance` and `Balance by Exchange`.
- It does not prove that each external exchange or wallet was fully synced to the same cutoff.
- `baseline_source_activity.csv` records the first and last baseline transaction timestamp seen for each source plus whether that source still has balances in `Balance by Exchange`.

Use the light verification export set first. Reach for Roll Forward or Double-entry only when the simple reports cannot explain a mismatch.
