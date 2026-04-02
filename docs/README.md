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
- [Architecture overview](concepts/architecture-overview.md)
- [Reconciliation and tax architecture](concepts/reconciliation-tax-architecture.md)
- [Oracle boundaries](concepts/oracle-boundaries.md)
- [Transaction classification](concepts/transaction-classification.md)
- [Workspace model](concepts/workspace-model.md)
<!-- docs-maintenance:end concepts -->

## Common Tasks

<!-- docs-maintenance:start guides -->
- [Operator quickstart](guides/operator-quickstart.md)
- [Full operator workflow](guides/full-operator-workflow.md)
- [Write an adapter](guides/write-an-adapter.md)
<!-- docs-maintenance:end guides -->

## Reference Material

<!-- docs-maintenance:start reference -->
- [Baseline validation contract](reference/baseline-validation-contract.md)
- [Export checklist](reference/export-checklist.md)
- [Wallet inventory artifacts](reference/wallet-inventory-artifacts.md)
- [Timezone validation artifacts](reference/timezone-validation-artifacts.md)
- [Canadian crypto tax guide](reference/canadian-crypto-tax-guide.md)
- [Tax source map](reference/tax-source-map.md)
- [CoinTracking oracle artifacts](reference/cointracking-oracle-artifacts.md)
<!-- docs-maintenance:end reference -->

## Workspace Guidance

Use [workspace/README.md](workspace/README.md) for the mirrored repo guidance
that follows the external workspace layout.

## Current Status

<!-- docs-maintenance:start status -->
- [Current state](status/current-state.md)
- [Migration sequence](status/migration-sequence.md)
<!-- docs-maintenance:end status -->

## Standards

<!-- docs-maintenance:start standards -->
- [Engineering standards](standards/engineering.md)
- [Implementation working agreement](standards/implementation.md)
- [Commit standards](standards/commits.md)
<!-- docs-maintenance:end standards -->
