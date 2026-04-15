---
title: "Architecture Overview"
summary: "High-level map of the current bridge, the target pipeline, and the focused pages that own each major contract."
doc_type: concept
audience: human
owner: repo
status: active
nav_order: 10
---

TallyLot ships a typed Python package and CLI for source-backed intake,
reconciliation, checkpointing, accounting validation, output rendering, and
tax-oriented work.

## Core Shape

- `domain/` owns business models, enums, and value objects
- `application/` owns use-case orchestration over domain models and ports
- `ports/` defines narrow typed boundaries
- `infrastructure/` implements ports
- `adapters/` translates source and output formats
- `interfaces/` exposes CLI entry points over application capabilities

## Operating Model

- raw evidence and live operator artifacts live in an external workspace, not
  in the repo
- the repo owns code, tests, docs, templates, automation, and workspace
  guidance
- financial values stay in `Decimal`
- unsupported or ambiguous facts stay explicit as issues, reviews, or later
  stage-owned gaps

## Current Bridge

The live runtime bridge currently centers on:

- `EconomicActivityDraft`
- `TransactionFact`
- `balance_snapshots.csv`
- `balance_references.csv`

That bridge is:

- the current implementation seam
- the current delivery path
- the current parity baseline
- not the final architecture center

Current bridge contracts and artifact rules live in
[Current Bridge Contracts](current-bridge-contracts.md).

## Target Direction

The target runtime pipeline converges on:

`EvidenceSet -> ClaimSet -> EconomicFacts -> ReconciliationState -> Checkpoint -> Journal -> TaxInputs -> TaxOutputs`

The target model is stage-first and ontology-first:

- source evidence and source-backed checkpoints remain first-class
- reconciliation and checkpoint trust gates come before accounting and tax
- CoinTracking remains an edge output and oracle surface, not the core ledger
  model
- bridge classifications remain current runtime vocabulary, not the long-term
  ontology center

## System Boundaries

- raw evidence and operator artifacts live in the external workspace
- the repo owns code, tests, docs, templates, automation, and mirrored
  workspace guidance
- source adapters produce source-local observations, bridge outputs today, and
  later target-stage inputs
- reconciliation and checkpoints are trust gates, not renderer side effects
- accounting and tax consume accepted upstream truth; they do not repair source
  meaning
- repo-only dev tooling may evolve under a clearer `dev_support/` boundary
  later, but current live repo-only support remains `repo_support/`

## Contract Owners

Use these pages as the owning contract set:

- [Current Bridge Contracts](current-bridge-contracts.md)
  Live bridge contracts, bridge artifacts, and current schema rules.
- [Bridge To Target Mapping](bridge-to-target-mapping.md)
  Bridge-to-target mapping from current bridge boundaries into bounded
  proto-products during migration.
- [Pipeline Stage Contracts](pipeline-stage-contracts.md)
  Target stage products, responsibilities, and handoff guarantees.
- [First Slice Contract](../reference/first-slice-contract.md)
  Bounded Coinbase-first parity, replay, and allowed-drift contract.
- [Domain Ontology](domain-ontology.md)
  Target ontology, identity seams, and bridge-versus-target modeling rules.
- [Gaps And Readiness](gaps-and-readiness.md)
  Target shared blocker model, readiness model, and `SubjectRef` rules.
- [Transaction Classification](transaction-classification.md)
  Current bridge classification vocabulary and bridge-only rules.
- [Oracle Boundaries](oracle-boundaries.md)
  Runtime-versus-oracle boundary rules.
- [Reconciliation And Tax Architecture](reconciliation-tax-architecture.md)
  Trust gates, performance rules, and rollout alignment.

## Read Next

- [Current Bridge Contracts](current-bridge-contracts.md)
- [Bridge To Target Mapping](bridge-to-target-mapping.md)
- [Reconciliation And Tax Architecture](reconciliation-tax-architecture.md)
- [Pipeline Stage Contracts](pipeline-stage-contracts.md)
- [First Slice Contract](../reference/first-slice-contract.md)
- [Domain Ontology](domain-ontology.md)
- [Gaps And Readiness](gaps-and-readiness.md)
- [Oracle Boundaries](oracle-boundaries.md)
- [Transaction Classification](transaction-classification.md)
