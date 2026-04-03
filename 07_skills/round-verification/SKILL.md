---
name: round-verification
description: Use when reviewing a repair or import round in this repo, especially for verification exports, drift comparison, gate classification, issue logging, and round-log updates.
---

# Round Verification

Use this skill after a manual CoinTracking repair or import.

## Default workflow

1. Confirm the round exists in `05_outputs/logs/round_log.csv`.
2. Capture only the default verification set unless drift requires heavier exports.
3. Run `06_scripts/verification_compare.py`.
4. If a source has canonical artifacts, run `06_scripts/reconcile_source.py` against the relevant Trade Table slice or reference ledger slice.
5. Classify the result:
   - passed
   - hold
   - blocked_pending_review
6. Update:
   - `03_analysis/issues/issue_log.csv`
   - `03_analysis/issues/source_inventory.csv`
   - `05_outputs/logs/round_log.csv`

## Gate rules

- Stop on unexplained duplicates.
- Stop on new unexplained validate rows.
- Stop on new unexplained strict missing rows.
- Stop on unexplained balance drift.

## Default commands

```bash
python3 06_scripts/verification_compare.py \
  --reference-dir <prior_dir> \
  --current-dir 02_working/verification/<round_id> \
  --out-dir 02_working/verification/<round_id>/comparison
```

```bash
python3 06_scripts/reconcile_source.py \
  --source "<Source Name>" \
  --cointracking-ledger <trade_table_or_slice.csv> \
  --canonical-events 02_working/normalized/<source>/canonical_events.csv \
  --canonical-balances 02_working/normalized/<source>/canonical_balances.csv \
  --out-dir 02_working/normalized/<source>/reconcile
```
