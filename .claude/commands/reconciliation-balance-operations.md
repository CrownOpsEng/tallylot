# Reconciliation Balance Operations

Use this route when the task is to inspect balance coverage, run balance
checks, or summarize reconciliation status across one source or many.

1. Read:
   - `docs/concepts/reconciliation-tax-architecture.md`
   - `docs/concepts/oracle-boundaries.md`
   - `docs/standards/implementation.md`
2. For direct operator-style execution, use the runtime CLI:
   - `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot reconciliation balances inspect`
   - `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot reconciliation balances check`
   - `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot reconciliation balances summarize`
3. For agent execution, use the repo-local skill runner at
   `.agents/skills/reconciliation-balance-operations/scripts/reconciliation_balance_operations.py`
   instead of ad hoc shell loops or one-off Python snippets.
4. Run these steps in order:
   - inspect coverage first
   - run balance checks second
   - summarize dates and blockers third
5. Answer the latest-date question from the summary artifact:
   - `latest_portfolio_clean_date` is the portfolio-wide clean answer
   - `latest_clean_source_date` is the latest clean date among checked sources
   - `latest_observed_assertion_date` is the latest date seen in any check output
6. Use oracle commands only after the summary shows they are needed for
   explanation or trust validation.
