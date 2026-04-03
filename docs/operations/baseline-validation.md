# Baseline Validation

## Canonical Baseline

- Baseline export folder: `evidence/raw/portfolio/cointracking/2023-08-05_full_export/`
- Authoritative cutoff source: `Trade Table`
- Latest transaction timestamp detected: **2023-08-05 08:34:04**
- Delta window rule: start strictly after that timestamp

## Generated Artifact Package

Run:

```bash
uv run crypto-reconciliation baseline validate \
  --export-dir <workspace>/evidence/raw/portfolio/cointracking/2023-08-05_full_export \
  --output-dir <workspace>/analysis/reconciliation
```

Artifacts:

- `baseline_asset_snapshot.csv`
- `baseline_exchange_reconciliation.csv`
- `baseline_negative_balances.csv`
- `baseline_source_activity.csv`
- `baseline_cad_flow_by_type.csv`
- `baseline_cad_balance_by_exchange.csv`
- `baseline_summary.json`

## Artifact Intent

- `baseline_asset_snapshot.csv`: asset-level comparison between `Current Balance`
  and the asset totals implied by `Balance by Exchange`
- `baseline_exchange_reconciliation.csv`: the same comparison with a simple
  `matched` or `drift` status
- `baseline_negative_balances.csv`: ending balances below zero
- `baseline_source_activity.csv`: first and last transaction timestamps plus a
  balance-presence flag by source or exchange
- `baseline_cad_flow_by_type.csv`: CAD bought, sold, and fee totals by trade
  type
- `baseline_cad_balance_by_exchange.csv`: CAD ending balances by exchange
- `baseline_summary.json`: high-level counts and the detected latest timestamp
