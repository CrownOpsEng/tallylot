# Balance Reconciliation Artifacts

Use these artifacts when interpreting the balance reconciliation workflow.

## Coverage

- `balance_coverage.csv`
- `balance_coverage_summary.json`

Coverage statuses:

- `comparable`
- `missing_snapshots`
- `missing_evidence`
- `empty_source`

## Checks

- `balance_check_summary.csv`
- per-source `balance_assertions.csv`
- per-source `reconciliation_issues.csv`
- per-source `balance_assertion_summary.json`

Check statuses:

- `clean`
- `issues`
- `failed`
- `no_assertions`

## Summary

- `balance_reconciliation_summary.json`
- `balance_reconciliation_blockers.csv`

Date fields:

- `latest_portfolio_clean_date`
- `latest_clean_source_date`
- `latest_observed_assertion_date`
