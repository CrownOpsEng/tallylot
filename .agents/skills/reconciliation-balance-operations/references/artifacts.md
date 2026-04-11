# Balance Reconciliation Artifacts

Use these artifacts when interpreting the balance reconciliation workflow.

## Inspect

- `balance_inspect.csv`
- `balance_inspect_summary.json`

Inspect statuses:

- `ready`
- `missing_references`
- `no_balance_targets`
- `no_balance_inputs`

Cross-source ready statuses:

- `ready`
- `missing_location_inventory`
- `not_comparable`
- `not_applicable`

Inspect summary fields:

- `source_count`
- `inspect_status_counts`
- `cross_source_ready_counts`
- `input_mode_counts`
- `snapshot_origin_counts`
- `offline_ready_source_count`
- `cross_source_ready_source_count`
- `missing_reference_source_count`
- `no_balance_target_source_count`
- `no_balance_input_source_count`
- `missing_location_inventory_source_count`
- `not_comparable_source_count`
- `not_applicable_source_count`

## Checks

- `balance_check_summary.csv`
- per-source `balance_assertions.csv`
- per-source `reconciliation_issues.csv`
- per-source `balance_reconciliation_summary.json`

Check statuses:

- `clean`
- `issues`
- `failed`
- `no_balance_targets`
- `not_runnable`

Resolution modes:

- `offline`
- `hydrated`

Not-runnable reasons:

- `no_balance_inputs`

Selected reference fields:

- `balance_assertions.csv` includes `selected_reference_kind`
- `balance_check_summary.csv` includes `resolution_mode`
- `balance_check_summary.csv` includes `check_status`
- `balance_check_summary.csv` includes `not_runnable_reason`
- `balance_check_summary.csv` includes `selected_reference_kind_counts`

## Summary

- `balance_reconciliation_summary.json`
- `balance_reconciliation_blockers.csv`

Date fields:

- `latest_portfolio_clean_date`
- `latest_portfolio_resolved_reference_date`
- `latest_clean_source_date`
- `latest_resolved_reference_date`
- `latest_observed_assertion_date`
