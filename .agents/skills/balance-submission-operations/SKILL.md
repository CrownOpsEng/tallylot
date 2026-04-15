---
name: balance-submission-operations
description: >-
  Scaffold manual balance submission packages, inspect missing required values,
  and submit validated balances into shared reconciliation artifacts without
  guessing hidden facts. Use when the task is to prepare or run the manual
  balance submission workflow for one source.
---

# Balance Submission Operations

Use this skill for the manual balance submission path.

## Workflow

1. Start with `.claude/commands/balance-submission-operations.md` for the
   matching route checklist.
2. Scaffold the package first with
   `.agents/skills/balance-submission-operations/scripts/balance_submission_operations.py`.
3. Inspect the filled files before submit so missing required values are called
   out explicitly.
4. Submit only when the package is ready; do not guess `instrument_id`,
   timestamps, quantities, support refs, or identity values.
5. Use `$reconciliation-balance-operations` only after balance artifacts
   already exist.

## Preferred Execution

- For direct operator parity, use:
  - `make cli ARGS='checkpoint scaffold-balance-submission'`
  - `make cli ARGS='checkpoint submit-balances'`
- For agent execution, prefer:
  - `python3 .agents/skills/balance-submission-operations/scripts/balance_submission_operations.py run ...`

## Outputs

- Scaffold creates `README.md` plus `.example` templates under the submission
  package.
- Inspect reports missing required files and fields without materializing
  outputs.
- Submit writes `balance_snapshots.csv`, `balance_references.csv`, optional
  `location_inventory.csv`, plus `balance_submission_summary.json` and
  `balance_submission_issues.csv`.
