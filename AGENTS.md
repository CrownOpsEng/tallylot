# AGENTS.md

## Objective

Work in the rebuilt typed application architecture under
`src/tallylot/`. Treat the repo as code, tests, docs, templates,
and automation. Treat the live workspace as external to the repo.

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
| Code placement, typing, modularization, naming | `docs/architecture/engineering-standards.md` |
| Active implementation execution discipline | `docs/architecture/implementation-working-agreement.md`, `docs/architecture/commit-standards.md` |
| Reconciliation, checkpoint, journal, or tax-engine implementation | `docs/architecture/reconciliation-tax-implementation-plan.md` |
| Platform-agnostic boundaries, classification mapping, or migration order | `docs/architecture/oracle-and-input-boundaries.md`, `docs/architecture/transaction-classification-matrix.md`, `docs/architecture/implementation-migration-sequence.md` |
| Source or output adapter work | `docs/architecture/adapter-authoring.md` |
| External workspace layout and seeded files | `docs/operations/workspace-layout.md` |
| Operational state, manual workflow, or agent runbooks | `docs/README.md`, then the specific doc it routes you to |
| Workspace subtree conventions, checklists, or templates | `docs/workspace/README.md` |
| Commit messages, templates, and checkpoint behavior | `docs/architecture/commit-standards.md` |
| Final pre-close implementation checks | `.claude/commands/implementation-checkpoint.md` |

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
- Bootstrap the checked-in hooks:
  - `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.install_git_hooks`
- Prefer fresh VS Code workspace diagnostics for instant static-analysis feedback when the
  `vscode-problems` skill or MCP snapshot is available and current.
  Treat that signal as advisory only.
- For explicit local verification, prefer:
  - `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.run_quality_gates`
  - `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.run_quality_gates --full-tests`
  - `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run python -m tools.run_ci_parity_checks`
- Do not run `UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run pre-commit run --all-files` in addition to the parallel
  quality-gate runner unless you are debugging hook behavior itself.
- Use `tools.run_quality_gates --full-tests` as the normal final local verification command.
- Use `tools.run_ci_parity_checks` only when changes touch CI, packaging, release, or other
  workflow surfaces where local parity with GitHub Actions is worth the extra time.
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

- Treat `docs/architecture/reconciliation-tax-implementation-plan.md` as the implementation
  anchor for reconciliation, checkpointing, journaling, and tax computation.
- Do not treat CoinTracking as the live ledger for new architecture work.
  CoinTracking is now a compatibility and oracle layer.
- Do not treat CoinTracking tax or accounting reports as normal runtime inputs.
  They are development-only oracle support artifacts unless an explicit
  one-time checkpoint import workflow adopts them with provenance.
- Do not expand the current canonical event model into the long-term center of
  the system. New structural work should target the provider-neutral
  transaction fact model described in the implementation plan.
- Keep `pydantic` at boundaries:
  - config
  - external artifact parsing
  - report row validation
  - request validation
  - discovery-time manifest validation
- Keep domain models centered on frozen dataclasses, enums, and value objects.
- Follow `docs/architecture/implementation-working-agreement.md` during coding:
  - structure first
  - tests alongside behavior
  - refactor obvious shared seams during the task
  - commit at stable checkpoints without waiting to be reminded
- When work affects architecture, schema, or execution sequencing, update
  `ROADMAP.md` and the implementation plan together.
