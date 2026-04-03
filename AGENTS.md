# AGENTS.md

## Objective

Work in the rebuilt typed application architecture under `src/tallylot/`.
Treat the repo as code, tests, docs, templates, and automation. Treat the live
workspace as external to the repo.

## Invariants

- Do not add legacy wrappers, migration utilities, or one-off repair code.
- Do not add repo-local live workspace assumptions.
- Keep strict layer boundaries:
  - `domain` has no infrastructure imports
  - `application` depends on `domain` and `ports`
  - `infrastructure` implements `ports`
  - `interfaces` only orchestrates services
- Keep financial values in `Decimal`, never `float`.
- Surface unsupported or ambiguous data as explicit issues.
- Keep adapter metadata, implementation, and tests aligned.
- Update `ROADMAP.md` when making decisions that affect later rollout phases.

## Read Only What You Need

Start with this file, then load only the narrow doc required for the task.
Do not pre-load every repo doc by default.

| Task | Read |
| ---- | ---- |
| Code placement, typing, modularization, naming | `docs/standards/engineering.md` |
| Active implementation execution discipline | `docs/standards/implementation.md`, `docs/standards/commits.md` |
| Planning sequence, delivery slices, or rollout checkpoints | `ROADMAP.md` |
| Reconciliation, checkpoint, journal, or tax-engine implementation | `docs/concepts/reconciliation-tax-architecture.md` |
| Platform-agnostic boundaries, classification mapping, or migration order | `docs/concepts/oracle-boundaries.md`, `docs/concepts/transaction-classification.md`, `docs/status/migration-sequence.md` |
| Source or output adapter work | `docs/guides/write-an-adapter.md` |
| Docs structure, generated index sections, or doc placement | `AGENTS.md`, `docs/README.md` |
| External workspace layout and seeded files | `docs/concepts/workspace-model.md`, `docs/workspace/README.md` |
| Operational state or manual workflow | `docs/status/current-state.md`, `docs/guides/operator-quickstart.md`, `docs/guides/source-intake.md`, `docs/guides/normalize-screen-stage.md`, `docs/guides/verify-a-round.md`, `docs/guides/full-operator-workflow.md` |
| Repo-specific baseline and verification context | `docs/status/current-state.md`, `docs/reference/repository-history.md` |
| Workspace subtree conventions, checklists, or templates | `docs/workspace/README.md` |
| Commit messages, templates, and checkpoint behavior | `docs/standards/commits.md` |
| Final pre-close implementation checks | `.claude/commands/implementation-checkpoint.md` |

## Documentation Maintenance Rules

- Human docs live under `docs/`.
- `docs/workspace/` remains the mirrored workspace reference subtree.
- Agent routing and repo execution rules live in `AGENTS.md` and
  `.claude/commands/`.
- Agent-only repo routing and maintenance rules live in this file and
  `.claude/commands/`.
- Agent-only context must not live in `docs/` unless it is genuinely useful to
  humans.
- Every new doc must have one primary type: concept, guide, reference,
  standard, or status.
- Avoid duplicate routing pages. Prefer `README.md`, `docs/README.md`, and
  this file over adding another switchboard.
- Broad docs or repo-structure reshapes should land as checkpoint commits at
  stable slices, not as one giant umbrella commit unless the slice cannot be
  validated incrementally.

## Execution Rules

- This repo intentionally uses the external uv environment at
  `$HOME/.venvs/tallylot-py312`.
- The repo-root `.venv` file is a sentinel, not a virtualenv directory. Do not
  override it with ad hoc repo-local envs.
- For all `uv` commands in this repo, use:
  - `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv ...`
- Bootstrap each clone before doing stable work:
  - `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.install_git_hooks`
- Do not consider work ready until `markdownlint`, `ruff`, `mypy`, `pyright`,
  `pylint`, and `pytest` pass.
- Do not consider non-trivial work ready until the verified checkpoint commit
  already exists.
- Prefer fresh VS Code workspace diagnostics for instant static-analysis
  feedback when the `vscode-problems` skill or MCP snapshot is available and
  current. Treat that signal as advisory only.
- For explicit local verification, prefer:
  - `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.run_quality_gates`
  - `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.run_quality_gates --full-tests`
  - `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.run_ci_parity_checks`
- Do not run `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run pre-commit run --all-files` in addition to the parallel quality-gate runner unless you are debugging hook behavior itself.
- Use `tools.run_quality_gates --full-tests` as the normal final local
  verification command.
- Use `tools.run_ci_parity_checks` only when changes touch CI, packaging,
  release, or other workflow surfaces where local parity with GitHub Actions is
  worth the extra time.
- Do not run `tools.run_quality_gates --full-tests` immediately before
  `tools.run_ci_parity_checks`; the parity runner already includes the full
  quality gate pass.
- The commit-time `pytest` hook is intentionally fast:
  - `unit and not slow`
  - no coverage
  - run full `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run pytest` before closing substantial work
- Treat commits as stable checkpoints by default:
  - prefer small cohesive commits
  - avoid micro-commits with no rollback or review value
  - end the task on a clean, meaningful checkpoint commit
- Treat protected branches as PR-only landing surfaces:
  - do not push directly to `main`
  - do not bypass branch protection for ordinary delivery
  - do not force-push protected branches unless the user explicitly requests a
    one-time repair in the current thread after branch protection has been
    temporarily adjusted
  - after any explicit one-time repair, verify the remote branch tip and return
    to PR-only delivery before continuing
- Treat repo cleanup as forward-only by default:
  - do not run `rm -rf`, `git restore`, `git reset`, `git checkout --`, or
    other destructive rollback commands unless the user explicitly asks for
    that cleanup in the current thread
  - prefer additive fixes, follow-up commits, or leaving cleanup for the user
    over destructive local undo
- If a flat directory would exceed 2 same-prefix files for one capability,
  regroup that capability into a package in the same task.
- If a feature already has a package, keep new helpers inside that package
  instead of beside it as flat sibling modules.

## Workspace Configuration

Workspace resolution order:

1. `CRYPTO_RECON_WORKSPACE_ROOT`
2. repo config in `tallylot.toml`
3. default `~/tallylot-workspace`

## Current Runtime

- Python `3.12`
- `uv`
- CLI and library only
- Filesystem-backed storage implementation
- SQLite and provider-backed AI remain stubbed behind interfaces

## Current Build Direction

- Treat `docs/concepts/reconciliation-tax-architecture.md` as the
  implementation anchor for reconciliation, checkpointing, journaling, and tax
  computation.
- Do not treat CoinTracking as the live ledger for new architecture work.
  CoinTracking is now a compatibility and oracle layer.
- Do not treat CoinTracking tax or accounting reports as normal runtime
  inputs. They are development-only oracle support artifacts unless an
  explicit one-time checkpoint import workflow adopts them with provenance.
- Do not expand the current canonical event model into the long-term center of
  the system. New structural work should target the provider-neutral
  transaction fact model described in
  `docs/concepts/reconciliation-tax-architecture.md`.
- Keep `pydantic` at boundaries:
  - config
  - external artifact parsing
  - report row validation
  - request validation
  - discovery-time manifest validation
- Keep domain models centered on frozen dataclasses, enums, and value objects.
- Follow `docs/standards/implementation.md` during coding:
  - structure first
  - tests alongside behavior
  - refactor obvious shared seams during the task
  - commit at stable checkpoints without waiting to be reminded
- When work affects architecture, schema, or execution sequencing, update
  `ROADMAP.md` and `docs/concepts/reconciliation-tax-architecture.md`
  together.
