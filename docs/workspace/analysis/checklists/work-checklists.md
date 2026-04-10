---
title: "Checklists"
summary: "Repair and import round checklists for mirrored workspace analysis work."
doc_type: reference
audience: both
owner: repo
status: active
---

## Baseline repair round checklist

- [ ] Run `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.oracles.cli round scaffold` for the round
- [ ] Review `analysis/reconciliation/baseline_cad_flow_by_type.csv` and current status of `FIAT-001`
- [ ] Review open P1 items in `analysis/issues/issue_log.csv`
- [ ] Pull external evidence for each targeted issue
- [ ] Save raw source files to `evidence/raw/source/<source>/<capture_label>/`
- [ ] Generate or refresh `evidence/raw/source/<source>/<capture_label>/manifest.csv`
- [ ] Update `proof_path` and `proof_summary` before editing the external verification tool state
- [ ] Make repair(s) in the external verification tool
- [ ] Export Validate Transactions
- [ ] Export Missing Transactions with strict settings: `100%` amount accuracy, only `100%` matches hidden, time accuracy `-24h | +48h`
- [ ] Export Duplicate Transactions
- [ ] Export Current Balance
- [ ] Export Balance by Exchange
- [ ] Export Trade Table, Roll Forward, or Double-entry only if needed
- [ ] Store exports under `working/verification/<round_id>/`
- [ ] Update `external_action`, `verification_path`, `gate_result`, and `closed_at` in the issue log
- [ ] Update `outputs/logs/round_log.csv`
- [ ] Confirm whether `FIAT-001` changed and update it if needed

## Source import round checklist

- [ ] Confirm the source has a row in `analysis/issues/source_inventory.csv`
- [ ] Confirm the export window starts strictly after `2023-08-05 08:34:04`
- [ ] Save raw source files to `evidence/raw/source/<source>/<capture_label>/`
- [ ] Generate or refresh `evidence/raw/source/<source>/<capture_label>/manifest.csv`
- [ ] Run `source profile` and review timezone artifacts
- [ ] Run `source normalize` and review exception and review artifacts
- [ ] Run `source assemble` before reconciliation or candidate rendering
- [ ] Render `cointracking_candidate.csv` when needed
- [ ] Run `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.oracles.cli batch screen` on the candidate CSV and review the output
- [ ] Run `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.oracles.cli batch stage` only after the screen passes
- [ ] Run `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.oracles.cli round scaffold`
- [ ] Import exactly one source into the external verification workflow
- [ ] Export Validate Transactions
- [ ] Export Missing Transactions with strict settings: `100%` amount accuracy, only `100%` matches hidden, time accuracy `-24h | +48h`
- [ ] Export Duplicate Transactions
- [ ] Export Current Balance
- [ ] Export Balance by Exchange
- [ ] Export Trade Table, Roll Forward, or Double-entry only if needed
- [ ] Store exports under `working/verification/<round_id>/`
- [ ] Run `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.oracles.cli verification compare` against the prior state and save the comparison artifacts
- [ ] Review CAD rows in `Current Balance` and `Balance by Exchange` if the source touches fiat rails
- [ ] Update `analysis/issues/source_inventory.csv`
- [ ] Update `analysis/issues/issue_log.csv` for any new or changed issues
- [ ] Update `outputs/logs/round_log.csv`
- [ ] Proceed only if the gate passes
