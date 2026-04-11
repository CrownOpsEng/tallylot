---
name: reconciliation-balance-operations
description: >-
  Run neutral balance coverage inspection, balance checks, and reconciliation
  summaries for one source or many using the repo's runtime contracts. Use when
  the task is to answer the latest clean reconciliation date, diagnose balance
  blockers, or execute the balance workflow without ad hoc shell loops.
---

# Reconciliation Balance Operations

Use this skill for balance reconciliation workflow execution and diagnosis.

## Workflow

1. Start with the runtime commands or the bundled script. Do not write ad hoc
   shell loops over source directories.
2. Use `.claude/commands/reconciliation-balance-operations.md` when you need
   the repo's matching command-route checklist.
3. Assume assembled source datasets include canonical `balance_snapshots.csv`
   and, when available, unified `balance_references.csv`. Use
   `$balance-submission-operations` first when the source still needs the
   manual submission path.
4. Run coverage inspection first.
5. Run balance checks second.
6. Run reconciliation summary third.
7. Use oracle commands only when the summary shows they are needed for
   explanation or trust validation.

## Preferred Execution

- For direct operator parity, the public CLI is:
  - `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot reconciliation balances inspect`
  - `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot reconciliation balances check`
  - `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot reconciliation balances summarize`
- For agent execution, prefer:
  - `python3 .agents/skills/reconciliation-balance-operations/scripts/reconciliation_balance_operations.py run ...`

## Outputs

- Coverage artifacts describe whether a source is source-backed,
  resolved-reference, mixed-reference, missing-reference, missing-snapshots,
  or empty.
- Check artifacts write per-source `balance_assertions.csv`,
  `reconciliation_issues.csv`, and `balance_reconciliation_summary.json`.
- Cross-source corroboration sidecars include `cross_source_assertions.csv`,
  `cross_source_issues.csv`, and `cross_source_summary.json`.
- Summary artifacts answer:
  - latest portfolio clean date
  - latest portfolio resolved-reference date
  - latest clean source date
  - latest resolved-reference date
  - latest observed assertion date
  - blocker counts by source and reason

Read `references/artifacts.md` when you need the artifact semantics or path
layout.
