# Source Reconcile

Use this route when a rendered candidate or canonical slice needs a direct
comparison against a reference ledger extract.

1. run `source reconcile`
2. review `reconciliation_summary.json`
3. inspect `candidate_only.csv` and `reference_only.csv`
4. feed any real mismatches back into normalization, staging, or verification

Use this instead of manual spreadsheet diffs when the rows should match exactly.
