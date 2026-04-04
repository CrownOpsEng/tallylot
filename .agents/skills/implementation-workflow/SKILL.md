---
name: implementation-workflow
description: >-
  Start ordinary tallylot code changes with the repo's narrow implementation
  path. Use when the task is code design, implementation, refactoring, test
  writing, or checkpointing inside this repo.
---

# Implementation Workflow

Use this skill for the normal repo implementation path.

Pair it with global `code-change-safety` for cross-repo posture and with
`markdown` only when the task edits Markdown files.

## Workflow

1. Read only the narrow repo contracts first:
   - `AGENTS.md`
   - `docs/standards/engineering.md`
   - `docs/standards/implementation.md`
   - `docs/standards/commits.md`
   - `.claude/commands/implementation-checkpoint.md`
2. Confirm the owning layer, package, and final structure before editing.
3. Add or update the tests that define the behavior.
4. Implement the change and refactor obvious shared seams while the seam is open.
5. Use fresh editor diagnostics first when available, then targeted tests while
   iterating.
6. Before closing substantial work, run:
   - `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.run_quality_gates --full-tests`
7. Create the verified checkpoint commit before considering the task done.

## Focus

- keep strict typed layer boundaries
- keep `Decimal` for monetary values
- surface ambiguity as explicit issues
- update `ROADMAP.md` with architecture or sequencing changes
