# Reconciliation And Tax Build

Use this route for architecture, implementation, or repair work tied to the
reconciliation, checkpoint, accounting, and tax buildout.

1. Read `docs/concepts/reconciliation-tax-architecture.md` first.
2. Read these when the task touches boundaries or sequencing:
   - `docs/concepts/oracle-boundaries.md`
   - `docs/concepts/transaction-classification.md`
   - `docs/status/migration-sequence.md`
   - `docs/standards/implementation.md`
3. Confirm whether the task changes:
   - transaction facts
   - reconciliation rules
   - checkpoint assembly
   - journal rendering
   - tax policy
   - CoinTracking oracle parsing
4. If the task changes architecture or sequencing decisions, update
   `ROADMAP.md` in the same checkpoint.
5. Keep these boundaries:
   - build reconciliation before tax
   - keep facts provider-neutral before rendering compatibility outputs
   - keep CoinTracking-specific parsing and rendering in adapter or oracle code
   - keep CoinTracking tax and accounting reports out of runtime state
   - keep Ledger CLI behind a renderer port
   - keep tax policy behind a policy port
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
9. For balance coverage, checking, or reconciliation-date questions, use
   `.claude/commands/reconciliation-balance-operations.md` and the runtime
   `reconciliation balances` commands instead of ad hoc shell loops or
   repo-only batch scripts.
10. Emit explicit issues when the task uncovers unsupported behavior or deferred
   cases.
11. Refactor obvious shared seams, add tests for new behavior, and commit a
    verified checkpoint before closing the task.
