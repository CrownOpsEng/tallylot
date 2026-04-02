---
title: "Documentation"
summary: "Human-facing entrypoint for concepts, guides, reference material, standards, and current status."
doc_type: reference
audience: human
owner: repo
status: active
---

This docs set covers the typed runtime, operator workflows, workspace model,
artifact contracts, and repo standards.

## How Docs Are Organized

- Concepts explain why the system is shaped the way it is.
- Guides describe how to perform a task.
- Reference pages define factual contracts, artifacts, and workspace semantics.
- Standards capture repo implementation rules.
- Status pages describe the current implemented surface and active migration
  state.

## Start Here

- [Current state](status/current-state.md)
- [Operator quickstart](guides/operator-quickstart.md)
- [Architecture overview](concepts/architecture-overview.md)
- [Reconciliation and tax architecture](concepts/reconciliation-tax-architecture.md)
- [Engineering standards](standards/engineering.md)
- [Workspace model](concepts/workspace-model.md)

Agent-specific routing and repo execution rules live in
[AGENTS.md](../AGENTS.md), not in the human docs homepage.

## Core Concepts

<!-- docs-maintenance:start concepts -->
- [Architecture Overview](concepts/architecture-overview.md): High-level map of the typed application layers, workflow capabilities, and external workspace model.
- [Reconciliation And Tax Architecture](concepts/reconciliation-tax-architecture.md): Design anchor for the provider-neutral reconciliation, accounting, checkpoint, and tax system.
- [Oracle Boundaries](concepts/oracle-boundaries.md): Boundary rules for normal runtime inputs, adapter surfaces, and oracle-only artifacts.
- [Transaction Classification](concepts/transaction-classification.md): Canonical layered classification vocabulary for facts, projections, accounting, and tax.
- [Workspace Model](concepts/workspace-model.md): Conceptual overview of the external workspace, seeded files, and mirrored repo guidance.
<!-- docs-maintenance:end concepts -->

## Common Tasks

<!-- docs-maintenance:start guides -->
- [Operator Quickstart](guides/operator-quickstart.md): Shortest safe path through intake, normalization, staging, and verification.
- [Full Operator Workflow](guides/full-operator-workflow.md): Long-form runbook for the current operator workflow and round-close process.
- [Write An Adapter](guides/write-an-adapter.md): Rules, shape, testing, and tooling guidance for source and output adapters.
<!-- docs-maintenance:end guides -->

## Reference Material

<!-- docs-maintenance:start reference -->
- [Baseline Validation Contract](reference/baseline-validation-contract.md): Baseline oracle package, artifact list, and intent for validation output.
- [Export Checklist](reference/export-checklist.md): Verification export set and staging checklist for round-close work.
- [Wallet Inventory Artifacts](reference/wallet-inventory-artifacts.md): Artifact contract for location inventory outputs and evidence rows.
- [Timezone Validation Artifacts](reference/timezone-validation-artifacts.md): Artifact contract for timezone provenance outputs and validation issues.
- [Canadian Crypto Tax Guide](reference/canadian-crypto-tax-guide.md): Working CRA-aligned tax reference for the repo's Canadian crypto workflow.
- [Tax Source Map](reference/tax-source-map.md): Targeted routing from repo tax questions to CRA-aligned reference sources.
- [CoinTracking Oracle Artifacts](reference/cointracking-oracle-artifacts.md): Repo-safe reference for CoinTracking artifact families used only for development and validation.
<!-- docs-maintenance:end reference -->

## Workspace Guidance

Use [workspace/README.md](workspace/README.md) for the mirrored repo guidance
that follows the external workspace layout.

## Current Status

<!-- docs-maintenance:start status -->
- [Current State](status/current-state.md): Implemented runtime capabilities, current operational surface, and deferred areas.
- [Migration Sequence](status/migration-sequence.md): Incremental migration order from the legacy normalized flow to the provider-neutral fact model.
<!-- docs-maintenance:end status -->

## Standards

<!-- docs-maintenance:start standards -->
- [Engineering Standards](standards/engineering.md): Code placement, typing, modularity, and naming rules for the typed application.
- [Implementation Working Agreement](standards/implementation.md): Execution rules for shaping, verifying, refactoring, and checkpointing repo work.
- [Commit Standards](standards/commits.md): Conventional Commit, checkpoint, and PR body rules for stable repo history.
<!-- docs-maintenance:end standards -->
