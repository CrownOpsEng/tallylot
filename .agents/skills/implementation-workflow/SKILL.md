---
name: implementation-workflow
description: >-
  Start ordinary tallylot code changes with the repo's narrow implementation
  path. Use when the task is code design, implementation, refactoring, test
  writing, or checkpointing inside this repo.
---

# Implementation Workflow

Use this skill for the normal repo implementation path.

Pair it with `markdown` only when the task edits Markdown files. Invoke
`issue-workflow` when implementation uncovers meaningful out-of-scope repo
work that should be captured as a follow-up issue.

## Workflow

1. Read only the narrow repo contracts first:
   - `AGENTS.md`
   - `docs/standards/engineering.md`
   - `docs/standards/implementation.md`
   - `docs/standards/commits.md`
   - `.claude/commands/implementation-checkpoint.md`
2. Confirm the owning layer, package, final structure, and forward-looking
   architecture guidance before editing.
3. Add or update only the tests that define meaningful behavior, contracts, or
   regressions.
4. Implement the change and refactor obvious shared seams while the seam is open.
5. Use fresh editor diagnostics first when available, then targeted tests while
   iterating.
6. Before closing substantial work, run:
   - `make quality`
   - reserve `make quality-full`
     for the explicit full-suite override when a specific task needs it
7. After compaction or context loss, reload the same narrow standards before
   more edits or commits.
8. Create the verified checkpoint commit before considering the task done.
   Use the shell-safe commit/PR authoring path from
   `docs/standards/commits.md` whenever the structured metadata includes
   backticks, quotes, or other shell-sensitive text.

## Focus

- keep strict typed layer boundaries
- keep `Decimal` for monetary values
- surface ambiguity as explicit issues
- update `ROADMAP.md` with architecture or sequencing changes
