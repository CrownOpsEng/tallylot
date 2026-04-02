# Reconciliation And Tax Build

Use this route for architecture, implementation, or repair work tied to the
reconciliation, checkpoint, accounting, and tax buildout.

1. Read `docs/architecture/reconciliation-tax-implementation-plan.md` first.
2. Read these when the task touches boundaries or sequencing:
   - `docs/architecture/oracle-and-input-boundaries.md`
   - `docs/architecture/transaction-classification-matrix.md`
   - `docs/architecture/implementation-migration-sequence.md`
   - `docs/architecture/implementation-working-agreement.md`
3. Confirm whether the task changes:
   - transaction facts
   - reconciliation rules
   - checkpoint assembly
   - journal rendering
   - tax policy
   - CoinTracking oracle parsing
4. If the task changes architecture or sequencing decisions, update
   `ROADMAP.md` in the same checkpoint.
5. Keep the build direction:
   - reconciliation before tax
   - provider-neutral facts before compatibility projections
   - CoinTracking as oracle and compatibility layer only
   - CoinTracking tax and accounting reports are oracle-only, not normal
     runtime inputs
   - Ledger CLI behind a renderer port
   - tax policy behind a policy port
6. Keep `pydantic` at boundaries only:
   - config
   - row parsing
   - request validation
   - artifact schema validation
7. Preserve strict layer boundaries and `Decimal`-only financial handling.
8. Add or update tests for:
   - schema and invariants
   - reconciliation behavior
   - journal validation
   - tax outputs
9. Do not close work with silent unsupported behavior. Emit explicit issues and
   update roadmap follow-ups when the task reveals deferred cases.
10. Do not wait for the user to remind you to refactor an obvious shared seam,
    create structure before more feature code piles in, add tests for new
    behavior, or commit a stable verified checkpoint.
