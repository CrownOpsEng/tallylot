---
title: "Delivery Guardrails"
summary: "Control hierarchy, enforcement tiers, and exception handling for repo delivery and agent-assisted Git operations."
doc_type: standard
audience: human
owner: repo
status: active
nav_order: 40
---

Use this document when delivery safety, branch protection, PR landing, merge
metadata, or agent-default Git behavior is part of the task.

This standard exists to prevent a repeat of failures where policy was known in
prose but not enforced strongly enough at the platform, repo, or agent layer.

Before changing delivery or standards guidance, reload the repo's docs
structure, authoring rules, and baseline context from `AGENTS.md`,
`docs/README.md`, `docs/status/current-state.md`,
`docs/reference/repository-history.md`, `tools/docs_maintenance/cli.py`, and
`tools/docs_maintenance/metadata.py` so new material lands in the right repo
surface and follows the repo's documentation metadata rules.
Use `code-change-safety` for the repo-guidance reload path and pair it with the
`markdown` skill when the task edits Markdown or docs surfaces.

## Guardrail Priority

Apply delivery controls in this order:

1. platform-native enforcement
2. repo-native policy as code
3. repo standards and checklists
4. agent default behavior
5. one-time repair exceptions explicitly requested in the current thread

Do not rely on lower layers to compensate for a missing higher-layer control
when the higher-layer control is available.

## Default Delivery Posture

- protected branches are PR-only landing surfaces
- direct pushes to `main` are forbidden except for an explicit one-time repair
  requested in the current thread
- a merged `main` commit must not be rewritten when the original PR record
  needs to remain attached to the landing commit
- multi-checkpoint PRs land with a merge commit using
  `<pr title> (#<pr number>)`
- single-checkpoint PRs land with squash merge
- replaced PRs use the repo's neutral duplicate or superseded label as the
  primary closeout marker
- comments on replaced PRs are fallback-only, not the default

## Enforcement Tiers

### 1. Platform-Native Controls

Prefer GitHub controls that reject bad actions before they land:

- rulesets or branch protection that require pull requests
- required status checks
- required reviews
- blocked force pushes on protected branches
- stale-review dismissal or last-push review requirements when the repo wants
  post-push re-approval
- CODEOWNERS or equivalent reviewer routing for control-plane files

Control-plane files include:

- `.github/workflows/**`
- `.github/pull_request_template.md`
- `.github/CODEOWNERS`
- `AGENTS.md`
- `docs/standards/**`
- `.claude/commands/**`
- `tools/install_git_hooks.py`
- `tools/pre_commit_hook.py`
- `tools/validate_commit_message.py`
- `tools/validate_pr_metadata.py`
- `tools/run_quality_gates.py`
- `tools/run_ci_parity_checks.py`

If a repo policy depends on a platform-native control that is not enabled, call
that out as a real enforcement gap rather than assuming documentation is
enough.

### 2. Repo-Native Policy As Code

Encode the repo's delivery rules in versioned artifacts:

- commit-message validators
- PR-metadata validators
- hook installers and hook guards
- CI workflows
- contract tests that pin the standards
- templates that match the validators

When a delivery failure repeats or has high repair cost, add or tighten a
machine-checkable guard instead of only adding more prose.

### 3. Repo Standards And Checklists

Use standards docs and checkpoint routes to explain:

- why the rule exists
- what exact behavior is required
- what exceptions are allowed
- what evidence must be checked before delivery is called done

Checklist text should describe the audit path, not serve as the only barrier.
Standards work itself must verify whether a rule belongs in human docs, agent
routing, or repo-native automation before adding a new document or route.

### 4. Agent Defaults

Global skills and agent defaults should be conservative when repo rules are
missing:

- assume PR-only delivery for the default branch
- assume merged default-branch history should not be rewritten
- assume force-push is exceptional, not routine
- prefer neutral direct `Why:` and `What:` language
- re-check merge method and subject immediately before landing
- report unresolved policy gaps instead of silently improvising
- use the relevant safety and authoring skills up front rather than relying on
  mid-task memory

## Required Delivery Audit

Before calling delivery complete, verify and report:

- which repo standards were reloaded immediately before the action
- whether the branch shape matched the allowed merge method
- which checks were required and whether they passed
- whether the landing subject exactly matched the required format
- whether older superseded PRs were labeled correctly
- whether the final remote branch tip still matches the reviewed PR record

## Exception Handling

One-time repair exceptions must be:

- explicitly requested in the current thread
- limited to the exact repair step
- verified immediately afterward
- followed by a return to normal PR-only flow

Do not turn a repair exception into a standing workflow.

## Rollout Order

When strengthening delivery guardrails, prefer this order:

1. enable or tighten platform-native controls
2. add repo-native validators and tests
3. align templates and docs with the enforced behavior
4. update global skill defaults so repos without local standards still start
   from a safer baseline

Do not stop at the documentation layer when a stronger control is available.
