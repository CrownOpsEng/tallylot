# Implementation Checkpoint

Use this route before closing any non-trivial coding task.

1. Read:
   - `docs/IMPLEMENTATION_WORKING_AGREEMENT.md`
   - `docs/commit-standards.md`
2. Confirm the change still respects:
   - layer ownership
   - provider-neutral core design
   - oracle-only treatment for CoinTracking tax and accounting reports
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
   - `docs/RECONCILIATION_TAX_IMPLEMENTATION_PLAN.md`
   - any boundary, matrix, or migration docs affected
7. Create a stable checkpoint commit when the slice is coherent and verified.

Do not close the task with "I'll clean that up later" if the needed structural
fix is already obvious and bounded.
