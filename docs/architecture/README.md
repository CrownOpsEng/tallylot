# Architecture Docs

Use this folder for implementation-facing design and coding discipline.

Start here when the task changes structure, schema, layering, migration order,
or long-term system direction.

This folder owns design contracts and implementation rules. It does not own the
forward roadmap, current runtime inventory, or completed history.

## Read In This Order For Most Implementation Work

1. [`engineering-standards.md`](engineering-standards.md)
2. [`implementation-working-agreement.md`](implementation-working-agreement.md)
3. [`reconciliation-tax-implementation-plan.md`](reconciliation-tax-implementation-plan.md)

## Routing By Concern

- Code placement, typing, modularization, and naming:
  [`engineering-standards.md`](engineering-standards.md)
- Coding-time workflow, refactor expectations, quality gates, and checkpoint
  discipline:
  [`implementation-working-agreement.md`](implementation-working-agreement.md)
- Reconciliation, checkpoints, accounting, tax design, and fact-model
  direction:
  [`reconciliation-tax-implementation-plan.md`](reconciliation-tax-implementation-plan.md)
- Migration order, parity gates, and path retirement:
  [`implementation-migration-sequence.md`](implementation-migration-sequence.md)
- Runtime-versus-oracle boundaries:
  [`oracle-and-input-boundaries.md`](oracle-and-input-boundaries.md)
- Classification vocabulary and support tiers:
  [`transaction-classification-matrix.md`](transaction-classification-matrix.md)
- Source and output adapter rules:
  [`adapter-authoring.md`](adapter-authoring.md)
- Commit, PR, and checkpoint message policy:
  [`commit-standards.md`](commit-standards.md)

## Read Only When Needed

- [`oracle-and-input-boundaries.md`](oracle-and-input-boundaries.md)
- [`transaction-classification-matrix.md`](transaction-classification-matrix.md)
- [`implementation-migration-sequence.md`](implementation-migration-sequence.md)
- [`adapter-authoring.md`](adapter-authoring.md)
- [`commit-standards.md`](commit-standards.md)
