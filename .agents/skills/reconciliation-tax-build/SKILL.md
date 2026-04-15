---
name: reconciliation-tax-build
description: >-
  Start tallylot's core reconciliation, checkpoint, accounting, and tax build
  work with the repo's narrow architecture path. Use when the task changes fact
  modeling, reconciliation rules, checkpoint assembly, journal logic, or tax
  policy behavior.
---

# Reconciliation And Tax Build

Use this skill for architecture-sensitive core workflow work.

## Workflow

1. Read the narrow architecture path first:
   - `docs/concepts/reconciliation-tax-architecture.md`
   - `docs/concepts/oracle-boundaries.md`
   - `docs/concepts/transaction-classification.md`
   - `docs/status/migration-sequence.md`
   - `docs/standards/implementation.md`
   - `.claude/commands/reconciliation-tax-build.md`
2. Confirm whether the task changes facts, reconciliation, checkpoints,
   accounting, tax policy, or oracle-only compatibility code.
3. Keep provider-neutral facts at the center and keep CoinTracking-specific
   behavior in compatibility or oracle paths.
4. Add or update schema, invariant, reconciliation, or tax tests before
   implementing behavior.
5. Update `ROADMAP.md` in the same checkpoint when architecture or sequencing
   decisions move.
6. Finish with:
   - `make quality`
   - reserve `make quality-full`
     for the explicit full-suite override when a specific task needs it

## Focus

- build reconciliation before tax
- keep `pydantic` at boundaries only
- keep strict layer boundaries and `Decimal`-only financial handling
