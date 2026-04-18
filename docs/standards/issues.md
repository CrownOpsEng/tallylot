---
title: "Issue Standards"
summary: "Issue scope, privacy rules, template usage, and proactive follow-up issue handling for repo work."
doc_type: standard
audience: human
owner: repo
status: active
naming_scope: repo_policy
nav_order: 35
---

Use this document when opening issues, designing issue templates, or deciding
whether newly discovered work should become a separate tracked issue.

## Repo Issue Scope

Use repository issues only for repo-engineering work in this repository:

- code
- tests
- docs and standards
- templates and other control-plane files
- automation and CI
- refactor and maintenance work

Do not use repository issues for:

- personal reminders or private task lists
- external workspace-only chores
- raw evidence handling outside the repo
- vague backlog dumping with no concrete repo change

## Required Issue Structure

All repo issues should use the shared structure below, whether they come from
the GitHub form chooser or from a maintainer-authored blank issue:

- `Summary`
- `Problem`
- `Evidence`
- `Desired Outcome`
- `Acceptance Criteria`

Keep issue text concrete, reviewable, and scoped to one repo change or one
bounded follow-up theme.

## Privacy And Durability Rules

Issue content must stay safe to keep in the public repo history.

Do not include:

- personal information
- secrets, tokens, or credentials
- raw evidence copied from the external workspace
- wallet or account identifiers
- local absolute filesystem paths

Use sanitized summaries, neutral descriptions, and repo-relative paths instead.

## Template Selection

Use the GitHub issue forms under `.github/ISSUE_TEMPLATE/` by default:

- `Bug` for incorrect behavior, regressions, broken tooling, or failing policy
  enforcement
- `Workflow gap` for missing or awkward repo-supported paths that should become
  a supported capability
- `Ops follow-up` for tooling, standards, templates, guardrails, or other
  repo-maintenance work that should stay out of the current PR

Maintainers may still use a blank issue when needed, but the blank issue must
follow the same repo scope, privacy, and structure rules.

## Duplicate Handling

Before opening a new issue:

- search existing open issues first
- reuse the existing issue when it already captures the same repo work
- open a new issue only when the work is materially different or missing

Avoid splitting one bounded follow-up into several near-duplicate issues.

## Proactive Follow-up Issues

When implementation or PR hardening uncovers meaningful out-of-scope
repo-engineering work that should not land in the active PR:

- search for an existing issue first
- open a new issue immediately when no suitable issue exists
- keep the issue privacy-safe and repo-scoped
- use the standard issue structure instead of an ad hoc note

Do not defer follow-up issue creation until after merge, handoff, or a later
cleanup pass.

## PR Linkage Rules

Use pull request metadata to distinguish resolved issues from tracked follow-up
work:

- every PR must include an `Issue linkage:` section that makes the issue
  decision explicit before merge
- use `Issue linkage:` with `- Closes #123: ...` only when the PR actually
  resolves the issue
- use `Issue linkage:` with `- Refs #123` or `- Refs #123: ...` for
  non-closing tracked work that remains separate from the current PR
- use `Issue linkage:` with `- None: ...` only when no existing issue applies
  after search and the reason is stated directly in the PR body

When a follow-up issue is opened during implementation or hardening, link it
from the active PR before merge.
