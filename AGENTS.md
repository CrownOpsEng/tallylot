# AGENTS.md

## Objective

Work in the rebuilt typed application architecture under
`src/crypto_reconciliation/`. Treat the repo as code, tests, docs, templates,
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
| Code placement, typing, modularization, naming | `docs/engineering-standards.md` |
| Source or output adapter work | `docs/adapter-authoring.md` |
| External workspace layout and seeded files | `docs/workspace-layout.md` |
| Operational state, manual workflow, or agent runbooks | `docs/README.md`, then the specific doc it routes you to |
| Workspace subtree conventions, checklists, or templates | `docs/workspace/README.md` |
| Commit messages, templates, and checkpoint behavior | `docs/commit-standards.md` |

## Execution Rules

- Do not consider work ready until `ruff`, `mypy`, `pyright`, `pylint`, and
  `pytest` pass.
- Prefer the checked-in hooks:
  - `uv run pre-commit install --hook-type pre-commit --hook-type commit-msg`
  - `uv run pre-commit run --all-files`
- Treat commits as stable checkpoints by default:
  - prefer small cohesive commits
  - avoid micro-commits with no rollback or review value
  - end the task on a clean, meaningful checkpoint commit

## Workspace Configuration

Workspace resolution order:

1. `CRYPTO_RECON_WORKSPACE_ROOT`
2. repo config in `crypto-reconciliation.toml`
3. default `~/Documents/CryptoLedgerWorkspaces/crypto-reconciliation-2025`

## Current Runtime

- Python `3.12`
- `uv`
- CLI and library only
- Filesystem-backed storage implementation
- SQLite and provider-backed AI remain stubbed behind interfaces
