---
name: docs-authoring
description: >-
  Start tallylot docs, standards, and doc-like control-plane edits with the
  repo's actual authoring path. Use when the task edits repo docs, standards,
  README content, or docs-maintenance metadata.
---

# Docs Authoring

Use this skill for repo documentation and standards work.

Pair it with `markdown` for syntax and low-churn Markdown editing. Invoke
`planning` for planning-only work, and use `issue-workflow` when the task adds
issue templates, issue policy, or proactive follow-up issue handling.

## Workflow

1. Read the narrow authoring guidance first:
   - `AGENTS.md`
   - `docs/README.md`
   - `docs/status/current-state.md`
   - `docs/reference/repository-history.md`
   - `docs/standards/implementation.md`
   - `docs/standards/commits.md`
   - `tools/docs_maintenance/cli.py`
   - `tools/docs_maintenance/metadata.py`
2. Keep human docs under `docs/` and agent-only routing under `AGENTS.md` or
   `.claude/commands/`.
3. Prefer updating an existing page over adding a new switchboard.
4. Preserve frontmatter, generated markers, and doc type boundaries.
5. Keep tracked docs and control-plane text neutral, durable, and free of
   scratch workflow bookkeeping.
   Keep live docs enforcement script-owned; do not add live-repo Markdown or
   control-plane policy assertions to pytest.
   Planning docs may use ephemeral planning language when the document itself
   is a planning surface, but durable control-plane and delivery metadata must
   stay phase-free and roadmap-free.
6. Validate docs changes with:
   - `make docs-check`
7. When the change touches forward-looking target docs, titles, summaries, or
   sync-managed docs-home blurbs, reload `docs/standards/engineering.md` and
   run:
   - `make naming-check`
8. If the change also affects repo control-plane behavior, finish with the
   repo's broader quality gates before checkpointing.

## Focus

- one primary doc type per file
- neutral direct standards language
- repo-native metadata, links, and generated sections
