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
`planning` for planning-only work, and use `issue-workflow` when
implementation uncovers meaningful out-of-scope repo work that should be
captured as a follow-up issue.

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
4. Implement the change and refactor obvious shared boundaries while the code
   area is already in motion.
5. Use fresh editor diagnostics first when available, then targeted tests while
   iterating.
6. Before closing substantial work, run:
   - `make quality`
   - reserve `make quality-full`
     for the explicit full-suite override when a specific task needs it
7. When forward-looking target names, ids, directory families, titles, or
   summaries change, run:
   - `make naming-check`
8. After compaction or context loss, reload the same narrow standards before
   more edits or commits.
9. Create the verified checkpoint commit before considering the task done.
   Use the shell-safe commit/PR authoring path from
   `docs/standards/commits.md` whenever the structured metadata includes
   backticks, quotes, or other shell-sensitive text.
10. Keep durable delivery metadata and ordinary branch names phase-free and
    roadmap-free.
    Forward-looking planning docs may use ephemeral planning language only when
    the document itself is a planning surface.

## Focus

- keep strict typed layer boundaries
- keep `Decimal` for monetary values
- record ambiguity as explicit issues
- update `ROADMAP.md` with architecture or sequencing changes
