---
name: pr-review
description: >-
  Start tallylot's repo-native PR review loop with the local standards, route,
  and change-sensitive review checks. Use when the task is PR review,
  hardening, or review-loop recovery on an active branch or draft PR.
---

# PR Review

Use this skill for repeatable review passes on an active branch or draft PR.

## Workflow

1. Read the narrow PR review surface first:
   - `docs/standards/delivery-guardrails.md`
   - `docs/standards/implementation.md`
   - `docs/standards/commits.md`
   - `.claude/commands/pr-review.md`
2. Start from deterministic branch and PR facts rather than scratch notes.
3. Use
   `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.audit_pr_review`
   to identify the applicable surface groups, review domains, and required
   verification before calling a pass clean.
4. Repair findings in bounded slices, rerun the required checks for the
   repaired slice, and keep the PR draft until a full applicable-surface pass
   yields no new meaningful findings.
5. Use `issue-workflow`, `docs-authoring`, or `implementation-workflow` when
   the repair surface moves into those repo-local workflows.

## Focus

- cover every applicable changed surface group
- keep findings evidence-backed
- use the strongest broad verification family without skipping declared
  surface-specific checks
