# AGENTS.md

## Objective

Work in the rebuilt typed application architecture under `src/crypto_reconciliation/`.
Treat the repo as code, tests, docs, and templates. Treat the live workspace as
external to the repo.

## Key Rules

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
