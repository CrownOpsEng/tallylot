---
name: docs-authoring
description: >-
  Start tallylot docs, standards, and doc-like control-plane edits with the
  repo's actual authoring path. Use when the task edits repo docs, standards,
  README content, or docs-maintenance metadata.
---

# Docs Authoring

Use this skill for repo documentation and standards work.

Pair it with global `markdown` for syntax and low-churn Markdown editing and
with `code-change-safety` when the change also touches automation or checkpoint
commits.

## Workflow

1. Read the narrow authoring surface first:
   - `AGENTS.md`
   - `docs/README.md`
   - `tools/docs_maintenance/cli.py`
   - `tools/docs_maintenance/metadata.py`
2. Keep human docs under `docs/` and agent-only routing under `AGENTS.md` or
   `.claude/commands/`.
3. Prefer updating an existing page over adding a new switchboard.
4. Preserve frontmatter, generated markers, and doc type boundaries.
5. Keep tracked docs and control-plane text neutral, durable, and free of
   scratch workflow bookkeeping.
6. Validate docs changes with:
   - `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.docs_maintenance sync --check`
7. If the change also affects repo control-plane behavior, finish with the
   repo's broader quality gates before checkpointing.

## Focus

- one primary doc type per file
- neutral direct standards language
- repo-native metadata, links, and generated sections
