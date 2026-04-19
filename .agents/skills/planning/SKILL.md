---
name: planning
description: >-
  Start planning-only repo work with the narrow standards-and-routing bundle
  before handing execution to the owning workflow skill.
---

# Planning

Use this skill for planning-only work across the repo. This is the repo's
general planning skill, not a replacement for execution workflows.

Hand execution off to `docs-authoring`, `implementation-workflow`,
`pr-review`, or `issue-workflow` once the plan is settled.

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
2. Add roadmap, migration, architecture, or area-specific docs only when the
   planning task actually needs that surface.
3. Keep durable surfaces phase-free and roadmap-free.
4. Keep roadmap-owned phase tags confined to planning and forward-looking docs.
5. Keep live docs enforcement in the owning script; do not turn pytest into the
   live-repo docs-policy gate.
6. Keep the plan narrow enough to hand execution to an existing workflow skill
   instead of duplicating that workflow here.

## Focus

- planning-only repo work
- routing and skill handoffs
- docs-check ownership and validator placement
- delivery metadata policy
