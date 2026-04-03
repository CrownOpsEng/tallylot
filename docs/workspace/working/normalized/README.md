# Normalized Files

Place deterministic normalized source artifacts here after profiling and field normalization.

Do not treat files here as raw evidence. The raw source must remain in `evidence/raw/source/`.

Per-source folders should use the typed pipeline artifact set:

- `profile.json`
- `profile_inventory.csv`
- `timezone_issues.csv`
- `canonical_events.csv`
- `canonical_balances.csv`
- `exceptions.csv`
- `normalization_reviews.csv`
- `cointracking_candidate.csv`
- `wallet_inventory.csv`
- `normalization_summary.json`

`cointracking_candidate.csv` is a rendered working candidate, not an approved import batch.
Only `working/import_batches/` should hold files that have passed overlap
screening and are approved for import.

`profile_inventory.csv` includes timezone provenance columns so agents and users
can inspect timestamp semantics without reopening raw files.

`timezone_issues.csv` holds blocking provenance conflicts. Non-blocking
assumptions are recorded in `normalization_reviews.csv`.
