---
title: "Documentation"
summary: "Human-facing entrypoint for concepts, guides, reference material, standards, and current status."
doc_type: reference
audience: human
owner: repo
status: active
---

The TallyLot docs cover the typed runtime, operator workflows, workspace
model, artifact contracts, and repo standards.

## How Docs Are Organized

- Concepts explain why the system is shaped the way it is.
- Guides describe how to perform a task.
- Reference pages define factual contracts, artifacts, and workspace semantics.
- Standards capture repo implementation rules.
- Status pages describe the current implemented capabilities and active migration
  state.

## Start Here

- [Current state](status/current-state.md)
- [Operator quickstart](guides/operator-quickstart.md)
- [Architecture overview](concepts/architecture-overview.md)
- [Current bridge contracts](concepts/current-bridge-contracts.md)
- [Bridge-to-target mapping](concepts/bridge-to-target-mapping.md)
- [Pipeline stage contracts](concepts/pipeline-stage-contracts.md)
- [Target contract primitives](reference/target-contract-primitives.md)
- [Target product artifacts](reference/target-product-artifacts.md)
- [First-slice contract](reference/first-slice-contract.md)
- [First downstream slice contract](reference/first-downstream-slice-contract.md)
- [Domain ontology](concepts/domain-ontology.md)
- [Reconciliation and tax architecture](concepts/reconciliation-tax-architecture.md)
- [Engineering standards](standards/engineering.md)
- [Workspace model](concepts/workspace-model.md)

Agent-specific routing and repo execution rules live in
[AGENTS.md](../AGENTS.md), not in the human docs homepage.

## Core Concepts

<!-- docs-maintenance:start concepts -->
- [Architecture Overview](concepts/architecture-overview.md): High-level map of the current bridge, the target pipeline, and the focused pages that own each major contract.
- [Reconciliation And Tax Architecture](concepts/reconciliation-tax-architecture.md): Design anchor for trust gates, performance rules, tax-policy architecture, and filing-critical rollout from the current bridge toward the target pipeline.
- [Current Bridge Contracts](concepts/current-bridge-contracts.md): Primary concept page for the live bridge contracts, bridge artifacts, and current schema rules.
- [Bridge To Target Mapping](concepts/bridge-to-target-mapping.md): Single authority for how live bridge boundaries map into the target pipeline during Phase 0 and the first bounded increment.
- [Pipeline Stage Contracts](concepts/pipeline-stage-contracts.md): Owning contract for the target pipeline products, stage responsibilities, handoff guarantees, and downstream decision boundaries.
- [Oracle Boundaries](concepts/oracle-boundaries.md): Boundary rules for normal runtime inputs, adapter inputs and outputs, and oracle-only artifacts.
- [Domain Ontology](concepts/domain-ontology.md): Primary concept page for the target economic ontology, identity boundaries, package direction, and bridge-versus-target modeling rules.
- [Transaction Classification](concepts/transaction-classification.md): Bridge-only classification vocabulary for the current fact-path bridge.
- [Gaps And Readiness](concepts/gaps-and-readiness.md): Owning concept page for the target gap model, readiness model, sidecar rules, and shared `SubjectRef` contracts.
- [Workspace Model](concepts/workspace-model.md): Conceptual overview of the external workspace, seeded files, and mirrored repo guidance.
- [Unified Adapter Architecture](concepts/unified-adapter-architecture.md): First-principles design anchor for the future unified adapter manifest, facets, adapter products, and deterministic verification model.
<!-- docs-maintenance:end concepts -->

## Common Tasks

Use the quickstart for the shortest session path, then use the task guides
below when you need the detailed procedure for one stage of the workflow.

<!-- docs-maintenance:start guides -->
- [Operator Quickstart](guides/operator-quickstart.md): Shortest safe path through intake, normalization, staging, and verification.
- [Source Intake](guides/source-intake.md): Detailed procedure for planning, applying, manifesting, and profiling a settled source capture.
- [Normalize, Screen, And Stage](guides/normalize-screen-stage.md): Detailed procedure for normalization review, candidate rendering, oracle screening, and staging.
- [Verify A Round](guides/verify-a-round.md): Detailed procedure for scaffolding, exporting, comparing, and closing a verification round.
- [Full Operator Workflow](guides/full-operator-workflow.md): Long-form runbook for the current operator workflow and round-close process.
- [Write An Adapter](guides/write-an-adapter.md): Rules, shape, testing, and tooling guidance for source and output adapters.
<!-- docs-maintenance:end guides -->

## Reference Material

<!-- docs-maintenance:start reference -->
- [Baseline Validation Contract](reference/baseline-validation-contract.md): Baseline oracle package, artifact list, and intent for validation output.
- [First Slice Contract](reference/first-slice-contract.md): Bounded contract for the default Coinbase-first proto-EvidenceSet and proto-ClaimSet increment.
- [First Downstream Slice Contract](reference/first-downstream-slice-contract.md): Bounded contract for the first Coinbase-first EconomicFacts, ReconciliationState, and Checkpoint increment.
- [Target Contract Primitives](reference/target-contract-primitives.md): Shared scalar forms, tuple contracts, dataset ids, and reusable id helpers for forward-looking target products.
- [Target Product Artifacts](reference/target-product-artifacts.md): Forward-looking dataset packaging, kernel filenames, and persistence layout for target pipeline products.
- [Export Checklist](reference/export-checklist.md): Verification export set and staging checklist for round-close work.
- [Wallet Inventory Artifacts](reference/wallet-inventory-artifacts.md): Artifact contract for location inventory outputs and evidence rows.
- [Timezone Validation Artifacts](reference/timezone-validation-artifacts.md): Artifact contract for timezone provenance outputs and validation issues.
- [Canadian Crypto Tax Guide](reference/canadian-crypto-tax-guide.md): Working CRA-aligned tax reference for the repo's Canadian crypto workflow.
- [Tax Source Map](reference/tax-source-map.md): Targeted routing from repo tax questions to CRA-aligned reference sources.
- [CoinTracking Oracle Artifacts](reference/cointracking-oracle-artifacts.md): Repo-safe reference for CoinTracking artifact families used only for development and validation.
- [Manual Balance Submission Artifacts](reference/manual-balance-submission-artifacts.md): Reference contract for scaffolded manual balance submission packages and their balance outputs.
- [Repository History](reference/repository-history.md): Reference note for the public baseline sequence and where ordinary forward development begins.
<!-- docs-maintenance:end reference -->

## Workspace Guidance

Use [workspace/README.md](workspace/README.md) for the mirrored repo guidance
that follows the external workspace layout.

## Current Status

<!-- docs-maintenance:start status -->
- [Current State](status/current-state.md): Implemented runtime capabilities, current operational capabilities, and deferred areas.
- [Migration Sequence](status/migration-sequence.md): Incremental migration order from the current bridge toward the target stage-first pipeline with parity gates and retirement rules.
- [Adapter Delivery Plan](status/adapter-delivery-plan.md): Filing-first plan for stabilizing current adapters now and deferring the unified adapter contract rewrite until after filing-critical work.
<!-- docs-maintenance:end status -->

## Standards

<!-- docs-maintenance:start standards -->
- [Engineering Standards](standards/engineering.md): Code placement, typing, modularity, and naming rules for the typed application.
- [Implementation Working Agreement](standards/implementation.md): Execution rules for shaping, verifying, refactoring, and committing repo work.
- [Commit Standards](standards/commits.md): Conventional Commit subjects, reviewable commit boundaries, and PR body rules for stable repo history.
- [Issue Standards](standards/issues.md): Issue scope, privacy rules, template usage, and proactive follow-up issue handling for repo work.
- [Delivery Guardrails](standards/delivery-guardrails.md): Control hierarchy, enforcement tiers, and exception handling for repo delivery and agent-assisted Git operations.
<!-- docs-maintenance:end standards -->
