# Reconciliation Balance Operations

Use this route when the task is to inspect balance readiness, run balance
checks, or summarize reconciliation status across one source or many.

1. Read:
   - `docs/concepts/reconciliation-tax-architecture.md`
   - `docs/concepts/oracle-boundaries.md`
   - `docs/standards/implementation.md`
2. Assume assembled source datasets already include `facts.csv` and, when
   available, `balance_snapshots.csv` and `balance_references.csv`. If a
   source still needs the manual submission path, start with
   `.claude/commands/balance-submission-operations.md`.
3. For direct operator-style execution, use the runtime CLI:
   - `make cli ARGS='reconciliation balances inspect'`
   - `make cli ARGS='reconciliation balances check'`
   - `make cli ARGS='reconciliation balances summarize'`
   - `check` runs offline by default; add `--hydrate-missing-references` only
     when provider hydration is intended.
4. For agent execution, use the repo-local skill runner at
   `.agents/skills/reconciliation-balance-operations/scripts/reconciliation_balance_operations.py`
   instead of ad hoc shell loops or one-off Python snippets.
5. Run these steps in order:
   - inspect readiness first
   - run balance checks second
   - summarize dates and blockers third
6. Current balance-check outputs also include cross-source corroboration
   sidecars:
   - `cross_source_assertions.csv`
   - `cross_source_issues.csv`
   - `cross_source_summary.json`
7. Answer the latest-date question from the summary artifact:
   - `latest_portfolio_clean_date` is the portfolio-wide clean answer
   - `latest_portfolio_resolved_reference_date` is the portfolio-wide clean
     date supported by resolved references
   - `latest_clean_source_date` is the latest clean date among checked sources
   - `latest_resolved_reference_date` is the latest clean source date
     supported by resolved references
   - `latest_observed_assertion_date` is the latest date seen in any check output
8. Use oracle commands only after the summary shows they are needed for
   explanation or trust validation.
