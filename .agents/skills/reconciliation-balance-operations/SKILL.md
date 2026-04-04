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
2. Run coverage inspection first.
3. Run balance checks second.
4. Run reconciliation summary third.
5. Use oracle commands only when the summary shows they are needed for
   explanation or trust validation.

## Preferred Execution

- For direct operator parity, the public CLI is:
  - `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot reconciliation balances inspect`
  - `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot reconciliation balances check`
  - `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot reconciliation balances summarize`
- For agent execution, prefer:
  - `python3 .agents/skills/reconciliation-balance-operations/scripts/reconciliation_balance_operations.py run ...`

## Outputs

- Coverage artifacts describe whether a source is comparable yet.
- Check artifacts write per-source `balance_assertions.csv`,
  `reconciliation_issues.csv`, and `balance_assertion_summary.json`.
- Summary artifacts answer:
  - latest portfolio clean date
  - latest clean source-backed date
  - latest observed assertion date
  - blocker counts by source and reason

Read `references/artifacts.md` when you need the artifact semantics or path
layout.
