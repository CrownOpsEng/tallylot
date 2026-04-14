# Source Diff

Use this route when a rendered candidate or fact-derived slice needs a direct
row comparison against a reference ledger extract.

1. run `make oracle ARGS='source diff'`
2. review `diff_summary.json`
3. inspect `candidate_only.csv` and `reference_only.csv`
4. feed any real mismatches back into normalization, staging, or verification

Use this instead of manual spreadsheet diffs when the rows should match exactly.
