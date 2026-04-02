# Export Checklist

## Canonical baseline already captured

Located in `evidence/raw/portfolio/cointracking/2023-08-05_full_export/`

## During baseline repair rounds

Always export to `working/verification/<round_id>/`:

- Validate Transactions
- Missing Transactions using strict settings: `100%` amount accuracy, only `100%` matches hidden, time accuracy `-24h | +48h`
- Duplicate Transactions
- Current Balance
- Balance by Exchange

Only export if needed:

- Trade Table
- Roll Forward in CAD
- Double-entry

After export:

- update `analysis/issues/issue_log.csv`
- update `outputs/logs/round_log.csv`

## After each source import

Always export to `working/verification/<round_id>/`:

- Validate Transactions
- Missing Transactions using strict settings: `100%` amount accuracy, only `100%` matches hidden, time accuracy `-24h | +48h`
- Duplicate Transactions
- Current Balance
- Balance by Exchange

Only export if needed:

- Trade Table
- Roll Forward in CAD
- Double-entry

After export:

- update `analysis/issues/issue_log.csv`
- update `analysis/issues/source_inventory.csv`
- update `outputs/logs/round_log.csv`

## When pulling a new raw external source

Always:

- save untouched files into `evidence/raw/source/<source>/<capture_id>/`
- run `06_scripts/source_manifest.py` against `evidence/raw/source/<source>/<capture_id>/`
- store the manifest at `evidence/raw/source/<source>/<capture_id>/manifest.csv`
- update `analysis/issues/source_inventory.csv`

Before copying an approved import file to `working/import_batches/`:

- run `06_scripts/overlap_check.py`
- review `overlap_summary.json`
- stop if the overlap check does not return `status: "pass"`

## Final closeout exports for `2025-12-31`

Store in `outputs/checkpoints/2025-12-31_final/`:

- Trade Table
- Current Balance
- Balance by Exchange
- Validate Transactions
- Missing Transactions using strict settings: `100%` amount accuracy, only `100%` matches hidden, time accuracy `-24h | +48h`
- Duplicate Transactions
- Double-entry
- Roll Forward in CAD
- Realized and Unrealized Gains in CAD
