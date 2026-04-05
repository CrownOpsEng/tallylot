# Balance Submission Operations

Use this route when the task is to scaffold a manual balance package, inspect
missing required values, or submit validated balances into canonical
reconciliation inputs.

1. Read:
   - `docs/concepts/reconciliation-tax-architecture.md`
   - `docs/standards/implementation.md`
   - `docs/workspace/working/supporting_artifacts/README.md`
   - `docs/workspace/analysis/reconciliation/README.md`
2. For direct operator-style execution, use:
   - `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot checkpoint scaffold-balance-submission`
   - `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot checkpoint submit-balances`
3. For agent execution, use
   `.agents/skills/balance-submission-operations/scripts/balance_submission_operations.py`
   instead of ad hoc shell loops or one-off Python snippets.
4. Run these steps in order:
   - scaffold the package first
   - inspect missing required files and values second
   - submit only when inspect shows the package is ready
5. Do not guess `instrument_id`, timestamps, quantities, support refs, or
   identity values. Surface missing values explicitly instead.
6. After a successful submit, use `reconciliation balances inspect`,
   `reconciliation balances check`, and `reconciliation balances summarize` to
   evaluate the canonical artifacts.
7. Treat successful manual submission as `operator_confirmed` runtime input,
   not as source-backed checkpoint evidence.
