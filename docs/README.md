# Docs

Use this index to find the smallest useful document instead of browsing the
whole folder.

## Start Here

- Coding or architecture work: start with [AGENTS.md](../AGENTS.md), then use
  [engineering-standards.md](engineering-standards.md),
  [IMPLEMENTATION_WORKING_AGREEMENT.md](IMPLEMENTATION_WORKING_AGREEMENT.md),
  and
  [RECONCILIATION_TAX_IMPLEMENTATION_PLAN.md](RECONCILIATION_TAX_IMPLEMENTATION_PLAN.md)
- Manual or operator workflow: use
  [OPERATIONS_QUICKSTART.md](OPERATIONS_QUICKSTART.md) first, then
  [MOP.md](MOP.md) when you need the full runbook
- Need a specific command, artifact, or route quickly: use
  [FILE_MAP.md](FILE_MAP.md)

## Build And Architecture

- [`engineering-standards.md`](engineering-standards.md): code placement,
  typing, modularization, and naming
- [`IMPLEMENTATION_WORKING_AGREEMENT.md`](IMPLEMENTATION_WORKING_AGREEMENT.md):
  coding-time execution contract for structure, tests, refactors, and commits
- [`RECONCILIATION_TAX_IMPLEMENTATION_PLAN.md`](RECONCILIATION_TAX_IMPLEMENTATION_PLAN.md):
  implementation anchor for reconciliation, checkpointing, accounting, and tax
- [`ORACLE_AND_INPUT_BOUNDARIES.md`](ORACLE_AND_INPUT_BOUNDARIES.md):
  platform-agnostic runtime-versus-oracle boundary rules
- [`TRANSACTION_CLASSIFICATION_MATRIX.md`](TRANSACTION_CLASSIFICATION_MATRIX.md):
  layered classification mapping and support tiers
- [`IMPLEMENTATION_MIGRATION_SEQUENCE.md`](IMPLEMENTATION_MIGRATION_SEQUENCE.md):
  migration order, dual-write strategy, and retirement gates
- [`adapter-authoring.md`](adapter-authoring.md): source and output adapter
  contracts and conventions
- [`commit-standards.md`](commit-standards.md): commit message format and
  checkpoint rules

## Operations And Runbooks

- [`PROJECT_STATE.md`](PROJECT_STATE.md): current runtime and implemented
  surface
- [`OPERATIONS_QUICKSTART.md`](OPERATIONS_QUICKSTART.md): shortest safe path
  through a normal working session
- [`MOP.md`](MOP.md): detailed procedure and round workflow
- [`FILE_MAP.md`](FILE_MAP.md): task-oriented route to docs, commands, and
  artifacts
- [`EXPORT_CHECKLIST.md`](EXPORT_CHECKLIST.md): verification export and staging
  checklist
- [`AI_SESSION_PROMPT.md`](AI_SESSION_PROMPT.md): compact repo-specific agent
  context

## Reference

- [`BASELINE_VALIDATION.md`](BASELINE_VALIDATION.md): baseline artifact package
  and validation contract
- [`WALLET_INVENTORY.md`](WALLET_INVENTORY.md): wallet inventory artifact
  semantics
- [`TIMEZONE_VALIDATION.md`](TIMEZONE_VALIDATION.md): timezone provenance and
  profile artifact contract
- [`CANADIAN_CRYPTOCURRENCY_TAXATION_GUIDE.md`](CANADIAN_CRYPTOCURRENCY_TAXATION_GUIDE.md):
  CRA-aligned working tax reference
- [`TAX_REFERENCE_MAP.md`](TAX_REFERENCE_MAP.md): targeted tax source routing
- [`TEST_SUITE_FOLLOWUPS.md`](TEST_SUITE_FOLLOWUPS.md): deferred test work
- [`cointracking_full_export_manifest.csv`](cointracking_full_export_manifest.csv):
  baseline export manifest reference

## Workspace Guides

- [`workspace/README.md`](workspace/README.md): repo-owned guidance and
  templates for workspace subtrees
- [`workspace-layout.md`](workspace-layout.md): external workspace shape and
  seeded files

## Agent Routes

- [`.claude/commands/source-intake.md`](../.claude/commands/source-intake.md):
  intake, profile, normalize, screen, stage, and reconcile route
- [`.claude/commands/round-verification.md`](../.claude/commands/round-verification.md):
  round scaffold and verification compare route
- [`.claude/commands/wallet-inventory.md`](../.claude/commands/wallet-inventory.md):
  wallet inventory rebuild route
- [`.claude/commands/normalization-exceptions.md`](../.claude/commands/normalization-exceptions.md):
  normalization review route
- [`.claude/commands/source-reconcile.md`](../.claude/commands/source-reconcile.md):
  candidate-versus-reference diff route
- [`.claude/commands/reconciliation-tax-build.md`](../.claude/commands/reconciliation-tax-build.md):
  architecture and implementation route for reconciliation, checkpointing,
  accounting, and tax
- [`.claude/commands/implementation-checkpoint.md`](../.claude/commands/implementation-checkpoint.md):
  final coding-quality, refactor, and commit checkpoint route
- [`.claude/commands/supporting-artifacts.md`](../.claude/commands/supporting-artifacts.md):
  PDF balance extraction and supporting evidence route
- [`.claude/commands/adapter-authoring.md`](../.claude/commands/adapter-authoring.md):
  adapter authoring and repair route
