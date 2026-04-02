# Operations Quickstart

Use this file for the shortest safe path between manual CoinTracking work and AI/script support.

## Start-of-session check

1. Read `00_docs/PROJECT_STATE.md`.
2. Read `00_docs/BASELINE_VALIDATION.md`.
3. Confirm the cutoff is still `2023-08-05 08:34:04`.
4. Open `03_analysis/issues/issue_log.csv` and `03_analysis/issues/source_inventory.csv`.
5. Review `03_analysis/reconciliation/baseline_cad_flow_by_type.csv` and confirm the current treatment for `FIAT-001`.
6. Review `03_analysis/reconciliation/baseline_source_activity.csv` and confirm the current treatment for `SYNC-001`.

## Fiat completeness check

Do not accept the negative CAD balance as harmless by default.

Use:

- `03_analysis/reconciliation/baseline_cad_flow_by_type.csv`
- `03_analysis/reconciliation/baseline_cad_balance_by_exchange.csv`
- `03_analysis/issues/issue_log.csv`

Default rule:

- if the fiat funding and withdrawal chain is not fully explained, keep `FIAT-001` open
- if the missing fiat leg exists outside CoinTracking, document that interface explicitly with proof
- if the fiat leg belongs in CoinTracking, backfill the missing fiat entries rather than relying on a negative cash balance as a proxy

## Source boundary check

Do not treat the export package's `last sync 2023-08-05` label as proof that every wallet and exchange was synced to that same effective cutoff.

Use:

- `03_analysis/reconciliation/baseline_source_activity.csv`
- `03_analysis/issues/issue_log.csv`

Default rule:

- keep `SYNC-001` open until the per-source boundary treatment is documented
- use source-specific overlap windows and overlap checks for delta exports rather than rewinding the entire project to the earliest source activity date
- do not use current external balances as a substitute for historical cutoff evidence

## Baseline repair round

1. Pick the specific issue IDs you are resolving.
2. Pull raw source evidence into `01_raw_exports/external/<source>/raw/`.
3. Run:

   ```bash
   python3 06_scripts/source_manifest.py \
     --source-dir 01_raw_exports/external/<source>/raw \
     --output 01_raw_exports/external/<source>/manifest.csv
   ```

4. Update `proof_path` and `proof_summary` in `03_analysis/issues/issue_log.csv`.
5. Seed the round:

   ```bash
   python3 06_scripts/round_scaffold.py \
     --round-id baseline_repair_round_01 \
     --phase baseline_repair \
     --source <source>
   ```

6. Make the CoinTracking edit manually.
7. Export only:
   - Validate Transactions
   - Missing Transactions using strict settings: `100%` amount accuracy, only `100%` matches hidden, time accuracy `-24h | +48h`
   - Duplicate Transactions
   - Current Balance
   - Balance by Exchange
8. Save those files into `02_working/verification/<round_id>/`.
9. Ask AI to compare the fresh exports against the prior state and update:
   - `cointracking_action`
   - `verification_path`
   - `gate_result`
   - `closed_at` when applicable
10. Update `05_outputs/logs/round_log.csv`.
11. If the round affects fiat-capable sources, re-check `FIAT-001`.

## New source import round

1. Confirm the source row exists in `03_analysis/issues/source_inventory.csv`.
2. Confirm the source export window begins strictly after `2023-08-05 08:34:04`.
3. Pull the raw export into `01_raw_exports/external/<source>/raw/`.
4. Run `source_manifest.py`.
5. Profile the raw source into `02_working/normalized/<source>/`:

   ```bash
   python3 06_scripts/profile_source.py \
     --source "<Source Name>" \
     --raw-dir 01_raw_exports/external/<source>/raw \
     --out-dir 02_working/normalized/<source>
   ```

6. Refresh wallet inventory explicitly when the source is wallet-scoped or when new wallet evidence was added:

   ```bash
   python3 06_scripts/wallet_inventory.py \
     --repo-root .
   ```

   Review `03_analysis/inventory/wallet_inventory.csv` and `03_analysis/inventory/wallet_inventory_issues.csv` before treating newly discovered identifiers as import-ready evidence.

7. Normalize the source into canonical outputs and a rendered candidate:

   ```bash
   python3 06_scripts/normalize_source.py \
     --source "<Source Name>" \
     --raw-dir 01_raw_exports/external/<source>/raw \
     --out-dir 02_working/normalized/<source> \
     --profile-json 02_working/normalized/<source>/profile.json
   ```

8. Stage the candidate into `02_working/import_batches/<source>/` only after overlap screening passes:

   ```bash
   python3 06_scripts/stage_import_batch.py \
     --candidate 02_working/normalized/<source>/cointracking_candidate.csv \
     --baseline-export-dir 01_raw_exports/cointracking/2023-08-05_full_export \
     --out-dir 02_working/import_batches/<source>
   ```

   Hold the batch if `stage_summary.json` reports `status: "blocked"`.
8. Copy or stage the approved file to `04_import_ready/` only after review.
9. Seed the round:

   ```bash
   python3 06_scripts/round_scaffold.py \
     --round-id post_import_<source>_01 \
     --phase post_import \
     --source <source>
   ```

10. Import exactly one source into CoinTracking manually.
11. Export only the default verification set, with `Missing Transactions` using strict settings: `100%` amount accuracy, only `100%` matches hidden, time accuracy `-24h | +48h`.
12. Save the exports into `02_working/verification/<round_id>/`.
13. Compare the fresh exports against the prior state:

   ```bash
   python3 06_scripts/verification_compare.py \
     --reference-dir <prior_export_dir> \
     --current-dir 02_working/verification/<round_id> \
     --out-dir 02_working/verification/<round_id>/comparison
   ```

Then:

1. Ask AI to review the comparison artifacts, classify any new exceptions, and confirm the balance movements match the source.
2. If canonical source artifacts exist, run `06_scripts/reconcile_source.py` against the relevant CoinTracking ledger slice or reference ledger slice.
3. Update `03_analysis/issues/source_inventory.csv`, `03_analysis/issues/issue_log.csv`, and `05_outputs/logs/round_log.csv`.
4. If the source touches CAD or fiat rails, review the CAD rows in `Current Balance` and `Balance by Exchange` before closing the round.

## When to escalate to heavier reports

Export `Trade Table`, `Roll Forward in CAD`, or `Double-entry` only when the default five reports cannot explain:

- new duplicates
- new validation errors
- new missing transactions
- unexplained asset balance drift

## Fast commands

Refresh the baseline artifact package:

```bash
python3 06_scripts/baseline_check.py \
  --export-dir 01_raw_exports/cointracking/2023-08-05_full_export \
  --out-dir 03_analysis/reconciliation
```

## Gate rule

Do not proceed to the next source until the current round has:

- fresh verification exports
- a deterministic comparison package under the round folder
- a `gate_result` in `05_outputs/logs/round_log.csv`
- any changed issue states recorded in `03_analysis/issues/issue_log.csv`
- any impacted fiat-layer issue updated, especially `FIAT-001`
