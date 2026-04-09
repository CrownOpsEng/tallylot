---
title: "Implementation Working Agreement"
summary: "Execution rules for shaping, verifying, refactoring, and checkpointing repo work."
doc_type: standard
audience: human
owner: repo
status: active
nav_order: 20
---

Use this document when actively coding in the repo. It is the execution
contract for how work should be shaped, verified, refactored, and committed so
future sessions do not depend on repeated reminders from the user.

This document complements:

- `docs/standards/engineering.md` for placement and modularity rules
- `docs/standards/commits.md` for commit format and checkpoint policy
- `docs/concepts/reconciliation-tax-architecture.md` for architecture direction
- `docs/status/migration-sequence.md` for no-big-bang migration order

## Repo-Native Tooling To Use

This repo uses the external uv environment at
`$HOME/.venvs/tallylot-py312`. The repo-root `.venv` file is a sentinel,
not a virtualenv directory. Use
`UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv ...` for repo
commands so `uv` does not create a workspace-local environment.

Prefer the repo's built-in tooling before inventing local workflows:

- inspect a fresh VS Code Problems snapshot first when the `vscode-problems`
  skill or MCP server is available, then fall back to CLI checks when the
  snapshot is stale, missing, or incomplete
- bootstrap each clone with
  `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.install_git_hooks`
  so the shared external environment is synced to the current checkout before
  hook installation; rerun that command if
  `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot ...`
  resolves a stale editable checkout after repo relocation or history rebuilds
- run broad verification with
  `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.run_quality_gates`
- run full verification before closing substantial work with
  `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.run_quality_gates --full-tests`
  The repo keeps the fast gate on the benchmark-backed phased schedule and the
  full gate on the benchmark-backed all-at-once schedule; do not change those
  defaults without rerunning the benchmark tools.
- mirror GitHub Actions locally when changing workflow, packaging, or release
  behavior with
  `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.run_ci_parity_checks`
- audit local CODEOWNERS coverage and live GitHub branch-protection settings
  together when changing delivery policy, branch protection, or CI guardrails
  with
  `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.audit_delivery_guardrails`
- audit PR review surface coverage with
  `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.audit_pr_review`
  and run the required review checks for the current diff with
  `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.run_pr_review_checks`
- scaffold new adapters with
  `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.scaffold_adapter ...`
- refresh generated pyright test-private execution environments with
  `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.sync_pyright_config`
  when adapter-local `tests/` packages are added or removed outside the
  scaffold tool; `tools.run_quality_gates` also refreshes that generated config
  and fails immediately when it had to update the file, so review and commit
  `pyrightconfig.tests.json` before rerunning
- refresh adapter golden fixtures with
  `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.refresh_adapter_goldens ...`
- benchmark test-slice changes with
  `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.benchmark_tests`
- benchmark quality-gate scheduling changes with
  `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.benchmark_quality_gates`

Do not replace these with ad hoc shell habits when the repo already has a
supported path.

`pyrightconfig.tests.json` is generated repo policy for test-private execution
environments. Do not hand-maintain adapter `executionEnvironments` in
`pyrightconfig.json`; update adapter-local test package layouts and rerun the
sync or quality-gate tool instead. If the quality-gate runner refreshes the
generated file, commit that change and rerun the gates.

When repo-native tooling and tests need shared support:

- keep production/runtime concerns out of `tools/` and `repo_support/`
- keep shared repo-only support in `repo_support/`, not in ad hoc duplicated
  test helpers or tool-local path constants
- keep `tools/` focused on entry points and task-specific dev modules

## Default Coding Posture

Agents should assume all of these are expected unless the task explicitly says
otherwise:

- keep the architecture aligned with
  `docs/concepts/reconciliation-tax-architecture.md`
- read the narrow forward-looking roadmap, architecture, migration, or owning
  boundary guidance before shaping a non-trivial change
- refactor when a clearer shared seam is already visible
- extract shared components before copy-paste patterns harden
- create or update tests alongside the implementation
- commit at stable checkpoints without waiting to be reminded
- do not close a non-trivial task until the verified checkpoint commit exists
- prefer typed, explicit models over loose dictionaries and convenience code

## Work Sequence

For non-trivial implementation work, use this order:

1. confirm the target seam and owning layer
2. create or update the typed models, contracts, or artifact schemas first
3. create or update tests that define the intended behavior
4. implement the behavior
5. refactor duplicated or cross-cutting logic into bounded shared components
6. run the relevant quality gates
7. checkpoint the work in a coherent commit

Do not start by patching call sites ad hoc and only later trying to discover
the right structure.

Before shaping a non-trivial fix, reload the narrow forward-looking guidance
that owns the change surface. Prefer the intended end-state seam over a local
temporary patch when the repo already documents the target ownership model.

## Refactor Expectations

Refactoring is expected when it clearly improves the current change, not only
when the user says the word "refactor."

Refactor during the task when any of these are true:

- the same logic is being copied into a second place
- a module is gaining a second responsibility
- a new feature would deepen coupling across layers
- repeated parsing, validation, or mapping rules are visible
- tests are getting repetitive because the production seam is wrong
- new work would make an existing hotspot materially worse

Do not defer an obvious structural fix if the change is already in the code you
are touching and the bounded refactor is cheaper than carrying the duplication
forward.

## Shared Component Rules

Extract shared code only to a specific, named seam.

Good extractions:

- adapter-local row parsers
- issue-rule modules
- reconciliation decision helpers
- tax policy mapping modules
- journal posting assemblers
- typed artifact writers or parsers

Avoid generic sinks:

- `helpers.py`
- `utils.py`
- `common.py`
- broad cross-layer convenience modules

For repo-native tooling and test support:

- use `repo_support/` only for narrow shared seams that are reused by multiple
  repo-native surfaces
- do not create generic `repo_support/helpers.py` or `repo_support/utils.py`
- if only one tool owns the logic, keep it local to that tool instead of
  promoting it into `repo_support/`

Shared components must stay owned by one layer and one concept.

## Test-First And Structure-First Guidance

Prefer structure-first or test-first work when introducing:

- new domain models or invariants
- new artifact schemas
- classification rules
- reconciliation logic
- journal posting rules
- tax treatment behavior

Minimum expectation:

- add focused unit tests for new decision logic
- add contract tests for new external artifact parsing or rendering
- add regression tests for fixed edge cases

Meaningful tests only:

- add tests for user-visible behavior, real contracts, non-trivial decision
  logic, and fixed regressions
- do not add trivial getter or setter tests, wording-only assertions, duplicate
  coverage at multiple layers, or call-order tests unless that order is the
  contract
- when tests become repetitive, treat that as a signal that the production seam
  may be wrong and refactor the seam instead of piling on more near-duplicate
  tests
- for repo-side agent scripts and internal workflow entry points, cover
  behavior in-process when a callable seam exists and reserve subprocess tests
  for the real launch boundary
- avoid duplicate in-process and subprocess tests that prove the same workflow
  behavior; once behavior is covered in-process, thin launch-boundary tests may
  use `@pytest.mark.no_cover`

Do not leave edge-case behavior implicit in implementation code without a test
that pins it down.

Mirror test structure to production structure whenever possible:

- `tests/unit/...` for business rules and local decision logic
- `tests/contract/...` for artifact contracts, parsers, renderers, and command
  interfaces
- `tests/e2e/...` only when the end-to-end workflow itself is the behavior

When a feature becomes a package, mirror that package structure in tests rather
than adding a growing pile of same-prefix test files.

## Commit Discipline

Agents should treat commits as part of finishing the work, not as optional
afterthoughts.

Expected behavior:

- make a commit when a bounded slice is stable and verified
- keep commits cohesive and reviewable
- prefer one commit per coherent reshape slice, not one commit per file
- keep each authored commit bounded to one reviewable concern with a clear
  rollback boundary
- before a checkpoint commit is pushed, amend or fix up a small, scoped
  follow-up patch into the owning non-pushed checkpoint when that avoids a
  low-value micro-commit, and update the amended commit message so its
  `Why:`, `What:`, and `Checks:` sections still describe the final content
- do not use repeated amend cycles to grow one broad checkpoint that should be
  split into separate commits with clearer review and rollback boundaries
- for large but separable scopes, create multiple bounded checkpoint commits
  before closeout instead of ending on one umbrella authored commit
- do not bundle unrelated fixes
- do not wait for the user to remind you to commit once the task has reached a
  real checkpoint
- when a refactor spans structure, routing, tooling, and tests, checkpoint each
  stable slice that already passes the narrow checks for that slice
- when opening a PR, use a Conventional Commit title and the structured PR body
  defined in `docs/standards/commits.md` because that metadata
  stays attached to the PR record and becomes the squash commit on `main` for
  the single-checkpoint exception
- keep PR, commit, and doc language neutral and direct: `Why:` should state the
  problem or constraint, `What:` should state the concrete repo change, and
  neither section should use rhetorical or promotional wording
- before merging a PR or rewriting mainline history, verify whether the pull
  request record must stay attached to the landing commit; if yes, do not
  rewrite that merge commit after merge
- if a multi-checkpoint PR merges with a merge commit, use
  `<pr title> (#<pr number>)` as the merge subject so the mainline log keeps
  the PR number visible
- if a repair PR replaces an older pull request, mark the old PR with the
  repo's neutral duplicate/superseded label before closing the repair loop
- add a neutral replacement comment only when the repo has no suitable label
  or the user explicitly asks for explanatory prose
- when the work uncovers follow-up or out-of-scope changes that do not belong
  in the current PR, search existing open issues first and create the issue
  immediately when no suitable issue already exists
- open only repo-engineering follow-up issues in this repository:
  - code
  - tests
  - docs and standards
  - templates and other control-plane files
  - automation and CI
- keep follow-up issues privacy-safe:
  - no personal information
  - no secrets or raw evidence
  - no wallet or account identifiers
  - no local absolute paths
- use the repo-standard issue structure from `docs/standards/issues.md`
- do not defer issue creation for out-of-scope work until after merge, handoff,
  or a later cleanup pass
- before closing a non-trivial task, ensure the commit already exists rather
  than leaving commit creation as follow-up work
- keep repo cleanup forward-only by default: do not use destructive rollback
  commands such as `rm -rf`, `git restore`, `git reset`, or `git checkout --`
  unless the user explicitly requests that cleanup in the current thread
- keep tracked docs, templates, and control-plane artifacts neutral and durable
- keep scratch review notes, temporary hardening ledgers, and compaction aids
  untracked; recover from deterministic repo facts instead

When not to commit:

- the worktree is inconsistent
- the tests for the slice are failing
- the checkpoint would be hard to review or roll back
- the current diff still contains multiple separable reviewable slices

Do not collapse a broad but separable refactor into one giant commit unless
the slice truly cannot be reviewed or validated incrementally.

## Compaction Recovery

Treat compaction or context loss as an ordinary operating condition.

When context is lost before more edits, commits, or delivery steps:

1. reload `git status` and the current branch tip
2. inspect the current diff and recent commits
3. inspect current PR metadata and changed files when PR work is active
4. reread only the narrow repo standards and start-skill docs for the active
   surface
5. reload the latest targeted verification results

Do not rely on tracked scratch notes, phase logs, or preserved review ledgers
to recover task state.

## Quality Gates

Default verification expectations:

- use fresh VS Code Problems diagnostics first for instant editor-grounded
  lint and type feedback when they are available and current
- targeted tests during development
- full relevant checks before closing substantial work

Preferred commands are already defined in `AGENTS.md`, but the operating rule
is:

- do not call work done with only local reasoning
- verify the changed behavior at the smallest useful level first
- then run `tools.run_quality_gates --full-tests` before closing the task
- escalate to `tools.run_ci_parity_checks` only when the change touches CI,
  packaging, release, or other workflow surfaces where exact GitHub Actions
  parity matters
- do not run `tools.run_quality_gates --full-tests` again immediately before
  `tools.run_ci_parity_checks`; the parity runner already includes it

For PR review and repair loops, choose verification by changed surface:

- `human_docs`: run `tools.docs_maintenance sync --check`
- `control_plane_text`: run docs maintenance plus the targeted policy tests
  declared by `tools.run_pr_review_checks`
- `repo_code_or_tooling`: run `tools.run_quality_gates --full-tests`
- `ci_or_release`: run `tools.run_ci_parity_checks`

When more than one surface group is present, the strongest broad verification
family wins, but any declared surface-specific targeted checks still apply for
touched control-plane paths.

If you are changing commit-time or suite-selection policy, keep the hook path
limited to bounded checkpoint checks and use the shared quality or parity
runners as the single broad verification source. Benchmark with
`tools.benchmark_tests` and `tools.benchmark_quality_gates` when you are
proposing a different test slice or quality-gate schedule, and do not expand
the hook path into a second full-suite verification pass.

## Migration Discipline

When a task touches a migrating surface:

- implement on the fact-based path first
- preserve external output projections only as needed
- do not add new behavior to the legacy center unless required for migration
- add parity coverage before retiring older paths

If the change would force a big-bang rewrite, the migration sequence is wrong.
Split the work into a smaller compatible slice.

## Workflow Integrity Rules

Keep workflow integrity rules explicit while the repo continues migrating.

- filesystem scans that enumerate user evidence must be deterministic
- tree-walking services should use the shared scan path with explicit output
  exclusions rather than ad hoc `rglob()` behavior
- archive inspection, archive safety limits, and archive-member issue reporting
  belong in the shared intake scan layer rather than in source adapters or CLI
  commands
- profiling and normalization outputs must not be written inside raw evidence
  trees
- evidence references recorded in normalized or checkpoint-supporting artifacts
  must stay source-relative and portable across workspaces
- docs, command routes, and agent entrypoints must stay aligned with the
  implemented runtime surface

## Adapter And Artifact Discipline

When adding or changing adapters:

- keep metadata, implementation, fixtures, and tests aligned
- use scaffold and golden-refresh tools instead of hand-rolling repetitive
  layout
- keep provider-specific parsing local to the adapter package
- extract shared behavior only when it is truly cross-provider and conceptually
  stable

When adding artifacts:

- define the schema explicitly first
- decide whether it is a runtime artifact, output-adapter artifact, or
  oracle-only artifact
- add contract coverage for parsers and renderers

## User-Independent Standards

Agents should not require repeated reminders to:

- keep layer boundaries intact
- preserve strong typing
- use `Decimal`
- log unsupported or ambiguous facts explicitly
- update roadmap and design docs when architecture changes
- extract shared seams when duplication becomes obvious
- add or update tests for new behavior
- create stable checkpoint commits

These are the default operating standards for the repo.

## Stop-And-Fix Triggers

Pause feature work and fix the structure first when:

- a new change would require importing across a forbidden layer boundary
- a module is becoming a new catch-all
- a hotspot module called out in `docs/standards/engineering.md` is about to
  absorb materially new behavior without first being split
- a flat directory would end up with more than 2 same-prefix files for one
  capability
- a feature already owns a package but new helpers are being left beside it as
  flat sibling modules
- CoinTracking-specific semantics are drifting into the core domain
- an oracle-only artifact is being treated like a required runtime input
- a quick patch would hide unsupported behavior instead of surfacing it

## Final Pre-Close Checklist

Before closing non-trivial work, confirm:

- the owning layer is still clear
- shared logic is extracted to the right seam
- tests pin the new behavior
- unsupported behavior is explicit
- docs are updated if architecture or workflow changed
- a stable checkpoint commit exists or is the immediate next step
