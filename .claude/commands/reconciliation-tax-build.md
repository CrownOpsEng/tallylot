# Reconciliation And Tax Build

Use this route for architecture, implementation, or repair work tied to the
reconciliation, checkpoint, accounting, and tax buildout.

1. Read `docs/concepts/reconciliation-tax-architecture.md` first.
2. Read these before shaping any non-trivial slice:
   - `ROADMAP.md`
   - `docs/status/migration-sequence.md`
   - `docs/status/current-state.md`
3. Read these when the task touches boundaries or sequencing:
   - `docs/concepts/oracle-boundaries.md`
   - `docs/concepts/transaction-classification.md`
   - `docs/standards/implementation.md`
4. Confirm whether the task changes:
   - `EvidenceSet` or `ClaimSet`
   - `EconomicFacts`
   - gap or readiness models
   - `ReconciliationState`
   - `Checkpoint`
   - `Journal`
   - `TaxInputs` or `TaxOutputs`
   - CoinTracking oracle parsing
5. If the task changes architecture or sequencing decisions, update
   `docs/concepts/reconciliation-tax-architecture.md` and `ROADMAP.md` in the
   same checkpoint, and update `docs/status/migration-sequence.md` when phase
   order, bridge rules, or checkpoint criteria changed.
6. Keep these boundaries:
   - build reconciliation before tax
   - keep facts provider-neutral before rendering compatibility outputs
   - keep CoinTracking-specific parsing and rendering in adapter or oracle code
   - keep CoinTracking tax and accounting reports out of runtime state
   - keep Ledger CLI behind a renderer port
   - keep tax policy behind a policy port
   - keep current facts plus balances as the MVP bridge while landing richer
     pipeline products incrementally
   - keep tax outputs described as `TaxInputs` plus selected policy, never as
     direct emissions from reconciled facts
   - keep the shared readiness slice definition exact: source, location,
     instrument, subject ref, continuity segment, checkpoint date, and tax
     year where relevant
   - prefer one bounded stage slice over building a speculative end-state
     framework before the next concrete filing-critical need exists
7. Keep `pydantic` at boundaries only:
   - config
   - row parsing
   - request validation
   - artifact schema validation
8. Preserve strict layer boundaries and `Decimal`-only financial handling.
9. Add or update tests for:
   - schema and invariants
   - reconciliation behavior
   - journal validation
   - tax outputs
10. Preserve test parity honestly. Do not delete tests without explicit human
    approval, do not silently remove assertions, and if tests move or
    consolidate, note what behavior remains covered and where.
11. For balance inspection, checking, or reconciliation-date questions, use
   `.claude/commands/reconciliation-balance-operations.md` and the runtime
   `reconciliation balances` commands instead of ad hoc shell loops or
   repo-only batch scripts.
12. Emit explicit issues when the task uncovers unsupported behavior or deferred
   cases.
13. Refactor obvious shared seams, add tests for new behavior, and commit a
    verified checkpoint before closing the task.
