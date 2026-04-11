---
name: balance-submission-operations
description: >-
  Scaffold manual balance submission packages, inspect missing required values,
  and submit validated balances into canonical reconciliation artifacts
  without guessing hidden facts. Use when the task is to prepare or run the
  manual balance submission workflow for one source.
---

# Balance Submission Operations

Use this skill for the manual balance submission path.

## Workflow

1. Start with `.claude/commands/balance-submission-operations.md` for the
   matching route checklist.
2. Scaffold the package first with
   `.agents/skills/balance-submission-operations/scripts/balance_submission_operations.py`.
3. Inspect the filled files before submit so missing required values surface
   explicitly.
4. Submit only when the package is ready; do not guess `instrument_id`,
   timestamps, quantities, support refs, or identity values.
5. Use `$reconciliation-balance-operations` only after canonical balance
   artifacts already exist.

## Preferred Execution

- For direct operator parity, use:
  - `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot checkpoint scaffold-balance-submission`
  - `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot checkpoint submit-balances`
- For agent execution, prefer:
  - `python3 .agents/skills/balance-submission-operations/scripts/balance_submission_operations.py run ...`

## Outputs

- Scaffold creates `README.md` plus `.example` templates under the submission
  package.
- Inspect reports missing required files and fields without materializing
  canonical outputs.
- Submit writes canonical `balance_snapshots.csv`,
  `balance_references.csv`, optional `location_inventory.csv`, plus
  `balance_submission_summary.json` and `balance_submission_issues.csv`.
