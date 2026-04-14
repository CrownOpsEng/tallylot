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
Use the repo-local workflow for the active surface on that reload path and pair
it with the `markdown` skill when the task edits Markdown or docs surfaces.
When the task changes GitHub-side delivery controls, run
`UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.audit_delivery_guardrails`
before and after the change so the local CODEOWNERS state and the live remote
branch protection state are audited together.

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
- pull requests open as draft by default
- a PR becomes ready for review only after the full issue-finding hardening
  loop yields no new meaningful findings
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
- PRs are never closed autonomously without explicit user instruction

## Enforcement Tiers

### 1. Platform-Native Controls

Prefer GitHub controls that reject bad actions before they land:

- rulesets or branch protection that require pull requests
- required status checks pinned to their owning app, not only named by context
- required reviews
- blocked force pushes on protected branches
- stale-review dismissal or last-push review requirements when the repo wants
  post-push re-approval
- CODEOWNERS or equivalent reviewer routing for control-plane files

If the repo currently has only one single review-capable collaborator, keep
required approving reviews and required code owner reviews as explicit deferred
platform gaps instead of pretending those review gates are enforced. Continue
to enforce the controls that remain achievable in a single-maintainer repo:
PR-only branch protection, strict required checks, blocked force pushes,
conversation resolution, and CODEOWNERS ownership routing for future reviewer
expansion.

Control-plane files include:

- `.agents/skills/**`
- `.github/actions/**`
- `.github/ISSUE_TEMPLATE/**`
- `.github/workflows/**`
- `.github/pull_request_template.md`
- `.github/CODEOWNERS`
- `AGENTS.md`
- `docs/standards/**`
- `.claude/commands/**`
- `repo_support/local_autofix.py`
- `repo_support/quality_gates.py`
- `repo_support/review_verification/**`
- `tools/install_git_hooks.py`
- `tools/pre_commit_hook.py`
- `tools/pre_push_hook.py`
- `tools/audit_delivery_guardrails.py`
- `tools/audit_pr_review.py`
- `tools/benchmark_quality_gates.py`
- `tools/evaluate_review_results.py`
- `tools/message_standards.py`
- `tools/run_review_check.py`
- `tools/run_pr_review_checks.py`
- `tools/validate_commit_message.py`
- `tools/validate_pr_metadata.py`
- `tools/run_quality_gates.py`
- `tools/verify_built_wheel.py`

If a repo policy depends on a platform-native control that is not enabled, call
that out as a real enforcement gap rather than assuming documentation is
enough.

### 2. Repo-Native Policy As Code

Encode the repo's delivery rules in versioned artifacts:

- commit-message validators
- PR-metadata validators
- issue forms and chooser config
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

PR review is a repeatable procedure, not an improvised pass. Review starts from
the changed surface groups in the current PR diff:

- `human_docs`
  - paths: `README.md`, `CHANGELOG.md`, and `docs/**` except
    `docs/standards/**`
  - review domains: factual accuracy, metadata and link integrity, audience
    and type placement
- `control_plane_text`
  - paths: `AGENTS.md`, `ROADMAP.md`, `.agents/skills/**`,
    `.claude/commands/**`, `docs/standards/**`,
    `.github/pull_request_template.md`, `.github/ISSUE_TEMPLATE/**`,
    `.github/CODEOWNERS`
  - review domains: policy correctness, route-skill-standard alignment,
    delivery behavior, compaction and context-loss recovery, issue and privacy
    handling
- `repo_code_or_tooling`
  - paths: `src/**`, Python under `tools/**`, `repo_support/**`, `tests/**`,
    and repo-root test support such as `conftest.py`
  - review domains: design and ownership, correctness and behavior, complexity
    and over-engineering, tests and regression value, naming and public
    terminology, documentation and control-plane alignment
- `ci_or_release`
  - paths: `.github/actions/**`, `.github/workflows/**`, and the repo's
    delivery planner, workflow helpers, and workflow-sensitive config surfaces
  - review domains: workflow correctness, delivery enforcement, metadata parity

Verification selection is deterministic and atomic:

- review domains are the union across every applicable surface group
- `tools.audit_pr_review` reports changed paths, grouped surfaces, review
  domains, the selected verification mode, selected checks, suppressed checks,
  and any unmapped paths
- pull-request CI is draft-aware:
  - draft and in-progress pull requests always run the always-visible PR metadata checks `commit-messages` and `pr-metadata`, then select the remaining atomic checks from the changed diff
  - once the pull request is no longer draft, `pr-review` switches to the full
    non-duplicated blocking suite before merge
  - it still runs `coverage-hotspots` as a non-blocking informative report
    whenever the selected plan includes `pytest-full` and that lane succeeds
- post-merge `main` CI, manual CI, and local planned runs also stay
  change-sensitive and select only the atomic checks needed for the diff
- the repo-installed `pre-commit` hook follows the same local planned
  selection model for staged paths instead of hard-running a fixed Python
  scanner bundle on every commit
- when `pytest-full` is selected, it suppresses the narrower targeted pytest
  subset checks so the same test evidence is not rerun under multiple wrappers;
  the planner suppresses the narrower targeted pytest subset checks
- `tools.run_quality_gates` is quality-only convenience tooling and does not
  decide PR or CI verification selection

Each PR review pass should:

- re-check prior fix surfaces first
- use `tools.audit_pr_review` to confirm the applicable surface groups, review
  domains, required verification family, and any unmapped paths before deciding
  the current pass found no new meaningful findings
- treat passing `tools.run_pr_review_checks` or broader verification as review
  evidence only; a green runner never replaces the mandatory red-team repair
  loop or decides the pass outcome
- describe each upcoming pass as issue-finding with open outcome; do not
  pre-label the next pass as clean, final, or publish-ready
- red-team one adjacent applicable surface group and look for up to 5 new
  unique evidence-backed findings for the current pass
- repair every finding from that pass before starting the next pass
- reload the narrow repo guidance needed for each repair surface before editing:
  use `AGENTS.md`, its task-routing table, and the owning roadmap,
  architecture, migration, or delivery docs surfaced by that route or by repo
  search hints instead of forcing one oversized preload bundle for every pass
- run the required review checks for the repaired slice and create bounded
  checkpoint commits during the loop using the repo's normal commit rules
- when a meaningful finding is real but should not expand the active PR, search
  existing issues first and open or link the follow-up issue before merge
- when a pass finds fewer than 5 new findings, report only those findings and
  keep the loop moving
- stop only after every applicable changed surface group has been revisited and
  a full applicable-surface loop yields no new meaningful findings; if the only
  remaining item is a minor finishing touch, repair it and finish once no other
  meaningful issues surface
- keep scratch tracking ephemeral and untracked

### 4. Agent Defaults

Global skills and agent defaults should be conservative when repo rules are
missing:

- assume PR-only delivery for the default branch
- assume PRs stay draft until the hardening loop is clean
- assume merged default-branch history should not be rewritten
- assume force-push is exceptional, not routine
- prefer neutral direct `Why:` and `What:` language
- frame each upcoming review pass as issue-finding with open outcome rather
  than as a pre-labeled clean or final pass
- re-check merge method and subject immediately before landing
- report unresolved policy gaps instead of silently improvising
- use the relevant safety and authoring skills up front rather than relying on
  mid-task memory

## PR-Only CI Enforcement

Pull request review enforcement stays separate from local commit hooks and
push-to-mainline CI.

- the `commit-messages` PR status validates the branch commit-message range and
  PR metadata on pull requests only
- the `pr-metadata` PR status validates the pull request title, body, and
  checkpoint linkage as its own visible required status
- the repo-installed `pre-push` hook mirrors `tools.validate_pr_metadata`
  against the current open pull request before push when `gh pr view` can
  resolve PR metadata for the branch
- the `plan-pr-review` workflow job audits the diff with
  `tools.audit_pr_review`, publishes the selected checks for transparency, and
  keeps the human review surface routing visible while choosing planned mode
  for draft PRs and full mode for non-draft PRs
- the `pr-review` PR status aggregates the selected blocking checks for draft
  PR plans and the full non-duplicated blocking suite for non-draft PRs; it
  uses explicit per-check jobs instead of one opaque umbrella runner so every
  required check stays visible in GitHub Actions
- required PR-only statuses must stay pinned to the GitHub Actions app through
  branch-protection check app IDs, not only by status context name
- push/mainline CI reuses the same atomic check catalog and deterministic
  planner for landed changes, but stays change-sensitive and is not a branch
  protection requirement
- `pr-review` is not a local commit-hook requirement

## Required Delivery Audit

Before calling delivery complete, verify and report:

- which repo standards were reloaded immediately before the action
- which applicable changed surface groups were reviewed
- whether the PR remained draft until the hardening procedure finished cleanly
- whether the branch shape matched the allowed merge method
- which checks were required and whether they passed
- whether meaningful out-of-scope repo findings were captured as issues and
  linked from the PR when they stayed out of scope
- whether any linked follow-up issue content remained privacy-safe and
  repo-scoped
- whether the landing subject exactly matched the required format
- whether older superseded PRs were labeled correctly
- whether the final remote branch tip still matches the reviewed PR record
- whether review requirements are truly enforced or explicitly deferred because
  the repo currently has only one single review-capable collaborator
- whether PR-only CI enforcement required `commit-messages`, `pr-metadata`,
  and `pr-review` for mergeable pull requests
- whether required PR-only statuses were pinned to the owning GitHub Actions
  app instead of relying on unpinned status-context names alone

## Exception Handling

One-time repair exceptions must be:

- explicitly requested in the current thread
- limited to the exact repair step
- verified immediately afterward
- followed by a return to normal PR-only flow

Do not turn a repair exception into a standing workflow.

## Compaction Recovery

After compaction or context loss, recover from deterministic delivery facts
instead of tracked scratch notes:

1. current branch tip and `git status`
2. current diff and recent commits
3. current PR title, body, and changed files when PR work is active
4. narrow delivery standards and the active hardening route
5. latest targeted verification results

## Rollout Order

When strengthening delivery guardrails, prefer this order:

1. enable or tighten platform-native controls
2. add repo-native validators and tests
3. align templates and docs with the enforced behavior
4. update global skill defaults so repos without local standards still start
   from a safer baseline

Do not stop at the documentation layer when a stronger control is available.
