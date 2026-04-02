# Normalized Files

Place deterministic normalized source artifacts here after profiling and field normalization.

Do not treat files here as raw evidence. The raw source must remain in `01_raw_exports/external/`.

Per-source folders should prefer the universal pipeline artifact set:

- `profile.json`
- `profile_inventory.csv`
- `timezone_issues.csv`
- `canonical_events.csv`
- `canonical_balances.csv`
- `exceptions.csv`
- `cointracking_candidate.csv`
- `normalization_summary.json`

`cointracking_candidate.csv` is a rendered working candidate, not an approved import batch.
Only `02_working/import_batches/` and `04_import_ready/` should hold files that have passed overlap screening and are approved for import.

`timezone_issues.csv` must be empty before a source is considered safe to normalize and stage.

Keep legacy source-specific artifacts only while they are still serving as parity fixtures during migration.
