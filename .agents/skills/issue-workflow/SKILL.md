---
name: issue-workflow
description: >-
  Start issue-template work and proactive follow-up issue creation with the
  repo's narrow issue policy and delivery path.
---

# Issue Workflow

Use this skill for GitHub issue forms, issue-writing policy, and proactive
follow-up issue creation.

Pair it with `markdown` for Markdown edits and reload `docs-authoring` when
the same task also changes repo standards, templates, or automation.

## Workflow

1. Read the narrow issue path first:
   - `AGENTS.md`
   - `docs/standards/issues.md`
   - `docs/standards/implementation.md`
   - `docs/standards/delivery-guardrails.md`
   - `docs/standards/commits.md`
   - `.claude/commands/issue-workflow.md`
2. Search existing open issues before creating a new one.
3. Open issues only for repo-engineering work in this repository.
4. Keep issue content privacy-safe:
   - no personal information
   - no secrets or raw evidence
   - no local absolute paths
5. Use the standard issue structure:
   - `Summary`
   - `Problem`
   - `Evidence`
   - `Desired Outcome`
   - `Acceptance Criteria`
6. When meaningful out-of-scope repo work appears, create the issue
   immediately instead of leaving it in scratch notes.
7. If a PR is active, link non-closing follow-up issues from `Follow-ups:` and
   use the shell-safe PR-body guidance in `docs/standards/commits.md` when the
   structured metadata contains backticks, quotes, or other shell-sensitive
   text.

## Focus

- repo-engineering scope only
- duplicate search before new issue creation
- privacy-safe issue content
- durable issue templates and policy
