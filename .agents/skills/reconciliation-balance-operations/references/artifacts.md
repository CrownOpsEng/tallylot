# Balance Reconciliation Artifacts

Use these artifacts when interpreting the balance reconciliation workflow.

## Coverage

- `balance_coverage.csv`
- `balance_coverage_summary.json`

Coverage statuses:

- `resolved_reference`
- `mixed_reference`
- `missing_snapshots`
- `missing_reference`
- `empty_source`

## Checks

- `balance_check_summary.csv`
- per-source `balance_assertions.csv`
- per-source `reconciliation_issues.csv`
- per-source `balance_reconciliation_summary.json`

Check statuses:

- `clean`
- `issues`
- `failed`
- `no_assertions`

Reference basis fields:

- `balance_assertions.csv` includes `reference_basis`
- `balance_check_summary.csv` includes `reference_basis_counts`

## Summary

- `balance_reconciliation_summary.json`
- `balance_reconciliation_blockers.csv`

Date fields:

- `latest_portfolio_clean_date`
- `latest_portfolio_resolved_reference_date`
- `latest_clean_source_date`
- `latest_resolved_reference_date`
- `latest_observed_assertion_date`
