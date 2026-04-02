# Docs

The repo keeps versioned guidance for both agents and manual operators. Treat
these files as the source of truth for the typed package and the supported
workflow around it.

## Core

- [`engineering-standards.md`](engineering-standards.md): code placement,
  typing, modularization, and naming
- [`adapter-authoring.md`](adapter-authoring.md): source and output adapter
  contracts and conventions
- [`workspace-layout.md`](workspace-layout.md): external workspace shape and
  seeded files
- [`IMPLEMENTATION_WORKING_AGREEMENT.md`](IMPLEMENTATION_WORKING_AGREEMENT.md):
  execution contract for refactoring, testing, and checkpoint commits during
  coding
- [`commit-standards.md`](commit-standards.md): commit message format and
  checkpoint rules

## Operations

- [`PROJECT_STATE.md`](PROJECT_STATE.md): current runtime and project-surface
  status
- [`RECONCILIATION_TAX_IMPLEMENTATION_PLAN.md`](RECONCILIATION_TAX_IMPLEMENTATION_PLAN.md):
  design and implementation anchor for the reconciliation, checkpoint,
  accounting, and tax-engine buildout
- [`ORACLE_AND_INPUT_BOUNDARIES.md`](ORACLE_AND_INPUT_BOUNDARIES.md):
  platform-agnostic runtime-versus-oracle boundary rules
- [`TRANSACTION_CLASSIFICATION_MATRIX.md`](TRANSACTION_CLASSIFICATION_MATRIX.md):
  layered classification and CoinTracking compatibility mapping
- [`IMPLEMENTATION_MIGRATION_SEQUENCE.md`](IMPLEMENTATION_MIGRATION_SEQUENCE.md):
  no-big-bang migration order and parity gates
- [`OPERATIONS_QUICKSTART.md`](OPERATIONS_QUICKSTART.md): shortest safe path
  through the current workflow
- [`MOP.md`](MOP.md): full manual of procedure for the current typed package
- [`FILE_MAP.md`](FILE_MAP.md): route to the smallest relevant artifact, command,
  or agent entrypoint
- [`EXPORT_CHECKLIST.md`](EXPORT_CHECKLIST.md): verification export and staging
  checklist
- [`NEXT_PHASE_EXECUTION_PLAN.md`](NEXT_PHASE_EXECUTION_PLAN.md): generic next
  round template using the typed commands
- [`AI_SESSION_PROMPT.md`](AI_SESSION_PROMPT.md): compact agent context

## Reference

- [`BASELINE_VALIDATION.md`](BASELINE_VALIDATION.md): baseline artifact package
  and validation contract
- [`WALLET_INVENTORY.md`](WALLET_INVENTORY.md): wallet inventory artifact
  semantics
- [`TIMEZONE_VALIDATION.md`](TIMEZONE_VALIDATION.md): timezone provenance and
  profile artifact contract
- [`TEST_SUITE_FOLLOWUPS.md`](TEST_SUITE_FOLLOWUPS.md): deferred test work
- [`CANADIAN_CRYPTOCURRENCY_TAXATION_GUIDE.md`](CANADIAN_CRYPTOCURRENCY_TAXATION_GUIDE.md):
  CRA-aligned working tax reference
- [`TAX_REFERENCE_MAP.md`](TAX_REFERENCE_MAP.md): targeted tax source routing
- [`cointracking_full_export_manifest.csv`](cointracking_full_export_manifest.csv):
  baseline export manifest reference

## Workspace Guides

- [`workspace/README.md`](workspace/README.md): repo-owned guidance and
  templates for workspace subtrees

## Agent Routes

- [`.claude/commands/source-intake.md`](../.claude/commands/source-intake.md):
  intake, profile, normalize, stage, and reconcile route
- [`.claude/commands/round-verification.md`](../.claude/commands/round-verification.md):
  round scaffold and verification compare route
- [`.claude/commands/wallet-inventory.md`](../.claude/commands/wallet-inventory.md):
  wallet inventory rebuild route
- [`.claude/commands/normalization-exceptions.md`](../.claude/commands/normalization-exceptions.md):
  normalization review route
- [`.claude/commands/source-reconcile.md`](../.claude/commands/source-reconcile.md):
  candidate-versus-reference diff route
- [`.claude/commands/reconciliation-tax-build.md`](../.claude/commands/reconciliation-tax-build.md):
  architecture and implementation route for the reconciliation, checkpoint,
  accounting, and tax buildout
- [`.claude/commands/implementation-checkpoint.md`](../.claude/commands/implementation-checkpoint.md):
  final coding-quality, refactor, and commit checkpoint route
- [`.claude/commands/supporting-artifacts.md`](../.claude/commands/supporting-artifacts.md):
  PDF balance extraction and supporting evidence route
- [`.claude/commands/adapter-authoring.md`](../.claude/commands/adapter-authoring.md):
  adapter authoring and repair route
