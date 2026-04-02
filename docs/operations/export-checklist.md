# Export Checklist

## Baseline Validation

Run:

```bash
uv run python -m tools.oracles.cli baseline validate \
  --export-dir <workspace>/evidence/raw/portfolio/cointracking/2023-08-05_full_export \
  --output-dir <workspace>/analysis/reconciliation
```

## Source Intake

- save untouched files into `evidence/raw/source/<source>/<capture_id>/`
- run `source manifest`
- run `source profile`
- run `source normalize`
- review `timezone_issues.csv`, `exceptions.csv`, and `normalization_reviews.csv`
- run `output render file` if you need the current tracker-import candidate

## Batch Gate

- run `uv run python -m tools.oracles.cli batch screen`
- review `stage_summary.json`
- stop if `passed` is `false`
- run `uv run python -m tools.oracles.cli batch stage` only after the screen passes

## Verification Exports After Any Repair Or Import

Always save to `working/verification/<round_id>/`:

- Validate Transactions
- Missing Transactions using strict settings: `100%` amount accuracy, only
  `100%` matches hidden, time accuracy `-24h | +48h`
- Duplicate Transactions
- Current Balance
- Balance by Exchange

Only export if needed:

- Trade Table
- Roll Forward in CAD
- Double-entry

Then:

- run `uv run python -m tools.oracles.cli verification compare`
- update `analysis/issues/issue_log.csv`
- update `analysis/issues/source_inventory.csv` when the round touches a source
- update `outputs/logs/round_log.csv`
