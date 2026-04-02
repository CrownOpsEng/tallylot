# Checklists

## Baseline repair round checklist

- [ ] Create `working/verification/<round_id>/` and seed `outputs/logs/round_log.csv`
- [ ] Review `analysis/reconciliation/baseline_cad_flow_by_type.csv` and current status of `FIAT-001`
- [ ] Review open P1 items in `analysis/issues/issue_log.csv`
- [ ] Pull external evidence for each targeted issue
- [ ] Save raw source files to `evidence/raw/source/<source>/<capture_id>/`
- [ ] Generate or refresh `evidence/raw/source/<source>/<capture_id>/manifest.csv`
- [ ] Update `proof_path` and `proof_summary` before editing CoinTracking
- [ ] Make repair(s) in CoinTracking
- [ ] Export Validate Transactions
- [ ] Export Missing Transactions with strict settings: `100%` amount accuracy, only `100%` matches hidden, time accuracy `-24h | +48h`
- [ ] Export Duplicate Transactions
- [ ] Export Current Balance
- [ ] Export Balance by Exchange
- [ ] Export Trade Table, Roll Forward, or Double-entry only if needed
- [ ] Store exports under `working/verification/<round_id>/`
- [ ] Run AI verification
- [ ] Update `cointracking_action`, `verification_path`, `gate_result`, and `closed_at` in the issue log
- [ ] Update `outputs/logs/round_log.csv`
- [ ] Confirm whether `FIAT-001` changed and update it if needed

## Source import round checklist

- [ ] Confirm the source has a row in `analysis/issues/source_inventory.csv`
- [ ] Confirm the export window starts strictly after `2023-08-05 08:34:04`
- [ ] Save raw source files to `evidence/raw/source/<source>/<capture_id>/`
- [ ] Generate or refresh `evidence/raw/source/<source>/<capture_id>/manifest.csv`
- [ ] Stage the cleaned working file in `working/import_batches/<source>/`
- [ ] Run `06_scripts/overlap_check.py` on the CoinTracking-ready candidate and review the output
- [ ] Copy the approved import file to `working/import_batches/`
- [ ] Create `working/verification/<round_id>/` and seed `outputs/logs/round_log.csv`
- [ ] Import exactly one source into CoinTracking
- [ ] Export Validate Transactions
- [ ] Export Missing Transactions with strict settings: `100%` amount accuracy, only `100%` matches hidden, time accuracy `-24h | +48h`
- [ ] Export Duplicate Transactions
- [ ] Export Current Balance
- [ ] Export Balance by Exchange
- [ ] Export Trade Table, Roll Forward, or Double-entry only if needed
- [ ] Store exports under `working/verification/<round_id>/`
- [ ] Run `06_scripts/verification_compare.py` against the prior state and save the comparison artifacts
- [ ] Run AI verification
- [ ] Review CAD rows in `Current Balance` and `Balance by Exchange` if the source touches fiat rails
- [ ] Update `analysis/issues/source_inventory.csv`
- [ ] Update `analysis/issues/issue_log.csv` for any new or changed issues
- [ ] Update `outputs/logs/round_log.csv`
- [ ] Proceed only if the gate passes
