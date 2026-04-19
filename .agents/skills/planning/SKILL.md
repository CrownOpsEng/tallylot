---
name: planning
description: >-
  Start planning-only repo work with the narrow planning bundle and hand
  execution to the owning workflow skill once the plan is settled.
---

# Planning

Use this skill for the repo's general planning path. It is the repo's general planning skill, not a replacement for execution workflows.

Pair it with `markdown` only when the planning task edits Markdown, and hand
execution off to `docs-authoring`, `implementation-workflow`, `pr-review`, or
`issue-workflow` once the plan is settled.

## Workflow

1. Read the narrow planning bundle first:
   - `AGENTS.md`
   - `docs/README.md`
   - `docs/status/current-state.md`
   - `docs/reference/repository-history.md`
   - `docs/standards/implementation.md`
   - `docs/standards/delivery-guardrails.md`
   - `docs/standards/commits.md`
   - `tools/docs_maintenance/cli.py`
   - `tools/docs_maintenance/metadata.py`
2. Confirm the planning surface, the owning execution workflow, and whether the
   task actually needs roadmap, migration, architecture, or area-specific docs
   before loading more context.
3. Keep durable surfaces phase-free and roadmap-free. Keep roadmap-owned phase
   tags confined to planning and forward-looking docs.
4. Keep live docs enforcement in the owning script. Use synthetic strings or
   temp repos for docs-tooling tests instead of turning pytest into the live-
   repo docs-policy gate.
5. Write an execution-ready plan with scope, exclusions, execution order,
   verification inventory or TDD-first tests, bounded checkpoint commits for
   non-trivial work, and the assumptions or defaults that affect execution.
6. Keep the plan compaction-safe: prefer concrete file paths, commands, and
   check ids, explain script-versus-pytest ownership when that boundary
   matters, and avoid duplicating execution details owned by another workflow
   skill.
7. Keep the plan narrow enough to hand execution to an existing workflow skill
   instead of duplicating that workflow here.
8. After compaction or context loss, reload the same narrow planning bundle
   before extending or revising the plan.

## Focus

- planning-only repo work
- execution-ready plans with clear verification, checkpoints, and assumptions
- routing and skill handoffs
- docs-check ownership and validator placement
- delivery metadata policy
