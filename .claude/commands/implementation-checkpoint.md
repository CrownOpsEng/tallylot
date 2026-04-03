# Implementation Checkpoint

Use this route before closing any non-trivial coding task.

1. Read:
   - `docs/architecture/implementation-working-agreement.md`
   - `docs/architecture/commit-standards.md`
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
   - targeted tests while iterating
   - `uv run python -m tools.run_quality_gates --full-tests` before closing
     substantial work
6. If architecture, schema, or sequencing changed, update:
   - `ROADMAP.md`
   - `docs/architecture/reconciliation-tax-implementation-plan.md`
   - any boundary, matrix, or migration docs affected
7. Create the stable checkpoint commit when the slice is coherent and verified.
   Do not close the task first and plan to commit afterward.

If a needed structural fix is already obvious and bounded, include it in the
same checkpoint instead of deferring it.
