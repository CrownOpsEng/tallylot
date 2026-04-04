# Implementation Checkpoint

Use this route before closing any non-trivial coding task.

1. Read:
   - `docs/standards/implementation.md`
   - `docs/standards/commits.md`
2. Confirm the change still respects:
   - layer ownership
   - provider-neutral core design
   - CoinTracking tax and accounting reports stay in comparison tooling, not
     runtime state
   - `Decimal`-only financial handling
3. Check whether the task should have triggered a bounded refactor:
   - duplicate logic appeared
   - a second responsibility was added to a module
   - a hotspot module absorbed more behavior
   - tests became repetitive because the seam is wrong
4. Confirm tests were added or updated for:
   - new decision logic
   - new parser or renderer contracts
   - fixed edge cases
5. Run the appropriate verification path:
   - use fresh VS Code Problems diagnostics first when they are available and current
   - targeted tests while iterating
   - `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.run_quality_gates --full-tests` before closing
     substantial work
   - `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.run_ci_parity_checks` when the change touches CI,
     packaging, release, or other workflow surfaces
6. If architecture, schema, or sequencing changed, update:
   - `ROADMAP.md`
   - `docs/concepts/reconciliation-tax-architecture.md`
   - any boundary, matrix, or migration docs affected
7. Create the stable checkpoint commit when the slice is coherent and verified.
   Do not close the task first and plan to commit afterward.
8. Confirm branch handling stayed PR-only for protected branches:
   - do not push directly to `main`
   - do not use branch-protection bypass for ordinary delivery
   - do not rewrite a merged `main` commit if the original pull request must
     remain attached to the landing commit; open a new repair pull request
     instead
   - if the user explicitly requested a one-time protected-branch repair,
     verify the remote branch tip afterward and return to PR-only flow

If a needed structural fix is already obvious and bounded, include it in the
same checkpoint instead of deferring it.
