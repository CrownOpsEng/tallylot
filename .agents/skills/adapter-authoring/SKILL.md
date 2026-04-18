---
name: adapter-authoring
description: >-
  Start tallylot source or output adapter work with the repo's adapter
  contract. Use when the task adds, repairs, or refactors adapter metadata,
  translation logic, rendering, or adapter tests.
---

# Adapter Authoring

Use this skill for adapter-focused work.

## Workflow

1. Read the adapter contract first:
   - `docs/concepts/unified-adapter-architecture.md`
   - `docs/guides/write-an-adapter.md`
   - `.claude/commands/adapter-authoring.md`
   - `docs/standards/engineering.md`
   - `docs/standards/implementation.md`
2. Keep adapter metadata, implementation, and tests aligned in one slice.
3. Keep normalization, rendering, and oracle-only behavior separated.
4. Prefer the scaffold path for new adapters:
   - `make scaffold-adapter ARGS='...'`
5. Add or update adapter tests beside the adapter package while implementing.
6. Run the standard quality gate before closing the adapter slice:
   - `make quality`
   - reserve `make quality-full`
     for the explicit full-suite override when a specific task needs it

## Focus

- explicit issues for ambiguity
- provider-neutral runtime boundaries
- no ad hoc adapter-local hacks
