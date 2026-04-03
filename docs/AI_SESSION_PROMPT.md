# AI Session Working Prompt

Use CoinTracking.info as the live ledger and this repo as the typed evidence,
normalization, staging, and verification toolchain.

Anchor to these facts first:

1. Canonical baseline folder:
   `evidence/raw/portfolio/cointracking/2023-08-05_full_export/`
2. Authoritative cutoff timestamp: `2023-08-05 08:34:04`
3. Delta work begins strictly after that timestamp unless a new baseline is
   intentionally adopted

Priority artifacts:

1. baseline validation package under `analysis/reconciliation/`
2. `analysis/issues/issue_log.csv`
3. `analysis/issues/source_inventory.csv`
4. `working/verification/`
5. `working/normalized/`
6. `working/import_batches/`
7. raw captures under `evidence/raw/source/`

Operational rules:

1. prefer the typed CLI commands over manual file shaping
2. do not stage or import a source while `timezone_issues.csv`, `exceptions.csv`,
   or `stage_summary.json` show unresolved blockers
3. update the round log after each seeded round and verification cycle
4. use `source reconcile` when a candidate or reference slice needs a
   deterministic row comparison
