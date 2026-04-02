# Implementation Working Agreement

Use this document when actively coding in the repo. It is the execution
contract for how work should be shaped, verified, refactored, and committed so
future sessions do not depend on repeated reminders from the user.

This document complements:

- `docs/architecture/engineering-standards.md` for placement and modularity rules
- `docs/architecture/commit-standards.md` for commit format and checkpoint policy
- `docs/architecture/reconciliation-tax-implementation-plan.md` for architecture direction
- `docs/architecture/implementation-migration-sequence.md` for no-big-bang migration order

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
- bootstrap hooks in each clone with
  `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.install_git_hooks`
- run broad verification with
  `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.run_quality_gates`
- run full verification before closing substantial work with
  `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.run_quality_gates --full-tests`
- mirror GitHub Actions locally when changing workflow, packaging, or release
  behavior with
  `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.run_ci_parity_checks`
- scaffold new adapters with
  `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.scaffold_adapter ...`
- refresh adapter golden fixtures with
  `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.refresh_adapter_goldens ...`
- benchmark test-slice changes with
  `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.benchmark_tests`

Do not replace these with ad hoc shell habits when the repo already has a
supported path.

## Default Coding Posture

Agents should assume all of these are expected unless the task explicitly says
otherwise:

- keep the architecture aligned with the implementation plan
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
- do not bundle unrelated fixes
- do not wait for the user to remind you to commit once the task has reached a
  real checkpoint
- when opening a PR, use a Conventional Commit title and the structured PR body
  defined in `docs/architecture/commit-standards.md` because that metadata
  becomes the squash commit on `main`
- before closing a non-trivial task, ensure the commit already exists rather
  than leaving commit creation as follow-up work

When not to commit:

- the worktree is inconsistent
- the tests for the slice are failing
- the checkpoint would be hard to review or roll back

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

If you are changing commit-time or suite-selection policy, benchmark first
instead of guessing:

- use `tools.benchmark_tests`
- preserve the fast commit-time slice unless a measured change justifies
  expanding it

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
- a hotspot module called out in `docs/architecture/engineering-standards.md` is about to
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
