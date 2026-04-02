# Docs

Use this index to find the smallest useful document instead of browsing the
whole folder.

This file routes by document ownership first. Use it when you need to know
which document owns which concern before reading further.

Naming convention:

- top-level docs and section docs use lowercase kebab-case
- `README.md` remains the deliberate exception for directory entrypoints
- `docs/workspace/` mirrors the runtime workspace structure, so directory names
  there may keep underscores when the runtime paths do

## Start Here

- Remaining planned work: [../ROADMAP.md](../ROADMAP.md)
- Completed milestones: [../CHANGELOG.md](../CHANGELOG.md)
- Current implemented runtime surface:
  [operations/project-state.md](operations/project-state.md)
- Coding or architecture work: start with [AGENTS.md](../AGENTS.md), then use
  [architecture/README.md](architecture/README.md)
- Manual or operator workflow: use
  [operations/README.md](operations/README.md)
- Tax, oracle, or historical reference material: use
  [reference/README.md](reference/README.md)
- Repo-owned workspace subtree guidance: use
  [workspace/README.md](workspace/README.md)
- Need a specific command, artifact, or route quickly: use
  [file-map.md](file-map.md)

## Ownership Map

- `ROADMAP.md`: remaining planned work, phase order, and delivery gates
- `CHANGELOG.md`: completed milestones and mainline history summaries
- `docs/architecture/`: design contracts, migration rules, and coding
  discipline
- `docs/operations/`: current runtime behavior, operator workflow, and
  artifact contracts
- `docs/reference/`: reference material that is not a runtime contract by
  default
- `docs/workspace/`: repo-owned guidance and templates for the external
  workspace structure
- `docs/file-map.md`: shortest route by task, command, artifact, or agent
  entrypoint

## Build And Architecture

- [`architecture/README.md`](architecture/README.md): route through the build
  and architecture docs by concern
- [`architecture/engineering-standards.md`](architecture/engineering-standards.md):
  code placement, typing, modularization, and naming
- [`architecture/implementation-working-agreement.md`](architecture/implementation-working-agreement.md):
  coding-time execution contract for structure, tests, refactors, and commits
- [`architecture/reconciliation-tax-implementation-plan.md`](architecture/reconciliation-tax-implementation-plan.md):
  implementation anchor for reconciliation, checkpointing, accounting, and tax
- [`architecture/oracle-and-input-boundaries.md`](architecture/oracle-and-input-boundaries.md):
  platform-agnostic runtime-versus-oracle boundary rules
- [`architecture/transaction-classification-matrix.md`](architecture/transaction-classification-matrix.md):
  layered classification mapping and support tiers
- [`architecture/implementation-migration-sequence.md`](architecture/implementation-migration-sequence.md):
  migration order, dual-write strategy, and retirement gates
- [`architecture/adapter-authoring.md`](architecture/adapter-authoring.md):
  source and output adapter contracts and conventions
- [`architecture/commit-standards.md`](architecture/commit-standards.md):
  commit message format and checkpoint rules

## Operations And Runbooks

- [`operations/README.md`](operations/README.md): route through runtime,
  runbook, and artifact-contract docs
- [`operations/project-state.md`](operations/project-state.md): current runtime
  and implemented surface
- [`operations/operations-quickstart.md`](operations/operations-quickstart.md):
  shortest safe path through a normal working session
- [`operations/mop.md`](operations/mop.md): detailed procedure and round
  workflow
- [`file-map.md`](file-map.md): task-oriented route to docs, commands, and
  artifacts
- [`operations/export-checklist.md`](operations/export-checklist.md):
  verification export and staging checklist
- [`operations/ai-session-prompt.md`](operations/ai-session-prompt.md):
  compact repo-specific agent context

## Reference

- [`reference/README.md`](reference/README.md): route through tax references,
  repo-safe oracle guidance, and deferred follow-ups
- [`operations/baseline-validation.md`](operations/baseline-validation.md):
  baseline artifact package and validation contract
- [`operations/wallet-inventory.md`](operations/wallet-inventory.md): wallet
  inventory artifact semantics
- [`operations/timezone-validation.md`](operations/timezone-validation.md):
  timezone provenance and profile artifact contract
- [`reference/canadian-cryptocurrency-taxation-guide.md`](reference/canadian-cryptocurrency-taxation-guide.md):
  CRA-aligned working tax reference
- [`reference/tax-reference-map.md`](reference/tax-reference-map.md): targeted
  tax source routing
- [`reference/test-suite-followups.md`](reference/test-suite-followups.md):
  deferred test work
- [`reference/cointracking-oracle-artifacts.md`](reference/cointracking-oracle-artifacts.md):
  generic guide to supported oracle artifact families for the historical
  portfolio-tracker baseline

## Workspace Guides

- [`workspace/README.md`](workspace/README.md): repo-owned guidance and
  templates for workspace subtrees
- [`operations/workspace-layout.md`](operations/workspace-layout.md): external
  workspace shape, seeded files, and migration mapping

## Agent Routes

- [`.claude/commands/source-intake.md`](../.claude/commands/source-intake.md):
  intake, profile, normalize, checkpoint, and render route
- [`.claude/commands/round-verification.md`](../.claude/commands/round-verification.md):
  dev-only oracle round scaffold and verification compare route
- [`.claude/commands/wallet-inventory.md`](../.claude/commands/wallet-inventory.md):
  checkpoint location inventory rebuild route
- [`.claude/commands/normalization-exceptions.md`](../.claude/commands/normalization-exceptions.md):
  normalization review route
- [`.claude/commands/source-diff.md`](../.claude/commands/source-diff.md):
  dev-only oracle candidate-versus-reference diff route
- [`.claude/commands/reconciliation-tax-build.md`](../.claude/commands/reconciliation-tax-build.md):
  architecture and implementation route for reconciliation, checkpointing,
  accounting, and tax
- [`.claude/commands/implementation-checkpoint.md`](../.claude/commands/implementation-checkpoint.md):
  final coding-quality, refactor, and commit checkpoint route
- [`.claude/commands/supporting-artifacts.md`](../.claude/commands/supporting-artifacts.md):
  PDF balance extraction and supporting evidence route
- [`.claude/commands/adapter-authoring.md`](../.claude/commands/adapter-authoring.md):
  adapter authoring and repair route
