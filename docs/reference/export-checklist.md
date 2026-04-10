---
title: "Export Checklist"
summary: "Verification export set and staging checklist for round-close work."
doc_type: reference
audience: human
owner: repo
status: active
nav_order: 20
---

## Baseline Validation

Run:

```bash
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.oracles.cli baseline validate \
  --export-dir <workspace>/evidence/raw/portfolio/cointracking/2023-08-05_full_export \
  --output-dir <workspace>/analysis/reconciliation
```

## Source Intake

- save untouched files into `evidence/raw/source/<source>/<capture_label>/`
- run `source manifest`
- run `source profile`
- run `source normalize`
- run `source assemble`
- review `timezone_issues.csv`, `exceptions.csv`,
  `normalization_reviews.csv`, and `fact_annotations.json`
- run `output render file` if the round needs `cointracking_candidate.csv`

## Batch Gate

- run `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.oracles.cli batch screen`
- review `stage_summary.json`
- stop if `passed` is `false`
- run `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.oracles.cli batch stage` only after the screen passes

## Verification Exports After Any Repair Or Import

Always save to `working/verification/<round_id>/`:

- Validate Transactions
- Missing Transactions using strict settings: `100%` amount accuracy, only
  `100%` matches hidden, time accuracy `-24h | +48h`
- Duplicate Transactions
- Current Balance
- Balance by Exchange

Only export if needed:

- Trade Table
- Roll Forward in CAD
- Double-entry

Then:

- run `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.oracles.cli verification compare`
- update `analysis/issues/issue_log.csv`
- update `analysis/issues/source_inventory.csv` when the round touches a source
- update `outputs/logs/round_log.csv`
