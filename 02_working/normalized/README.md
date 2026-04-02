# Normalized Files

Place deterministic normalized source artifacts here after profiling and field normalization.

Do not treat files here as raw evidence. The raw source must remain in `01_raw_exports/external/`.

Per-source folders should prefer the universal pipeline artifact set:

- `profile.json`
- `profile_inventory.csv`
- `canonical_events.csv`
- `canonical_balances.csv`
- `exceptions.csv`
- `cointracking_candidate.csv`
- `normalization_summary.json`

Keep legacy source-specific artifacts only while they are still serving as parity fixtures during migration.
