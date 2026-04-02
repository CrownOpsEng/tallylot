# Architecture Docs

Use this folder for implementation-facing design and coding discipline.

Start here when the task changes structure, schema, layering, migration order,
or long-term system direction.

This folder owns design contracts and implementation rules. It does not own the
forward roadmap, current runtime inventory, or completed history.

## Read In This Order For Most Implementation Work

1. [`../standards/engineering.md`](../standards/engineering.md)
2. [`../standards/implementation.md`](../standards/implementation.md)
3. [`reconciliation-tax-implementation-plan.md`](reconciliation-tax-implementation-plan.md)

## Routing By Concern

- Code placement, typing, modularization, and naming:
  [`../standards/engineering.md`](../standards/engineering.md)
- Coding-time workflow, refactor expectations, quality gates, and checkpoint
  discipline:
  [`../standards/implementation.md`](../standards/implementation.md)
- Reconciliation, checkpoints, accounting, tax design, and fact-model
  direction:
  [`reconciliation-tax-implementation-plan.md`](reconciliation-tax-implementation-plan.md)
- Migration order, parity gates, and path retirement:
  [`../status/migration-sequence.md`](../status/migration-sequence.md)
- Runtime-versus-oracle boundaries:
  [`oracle-and-input-boundaries.md`](oracle-and-input-boundaries.md)
- Classification vocabulary and support tiers:
  [`transaction-classification-matrix.md`](transaction-classification-matrix.md)
- Source and output adapter rules:
  [`adapter-authoring.md`](adapter-authoring.md)
- Commit, PR, and checkpoint message policy:
  [`../standards/commits.md`](../standards/commits.md)

## Read Only When Needed

- [`oracle-and-input-boundaries.md`](oracle-and-input-boundaries.md)
- [`transaction-classification-matrix.md`](transaction-classification-matrix.md)
- [`../status/migration-sequence.md`](../status/migration-sequence.md)
- [`adapter-authoring.md`](adapter-authoring.md)
- [`../standards/commits.md`](../standards/commits.md)
