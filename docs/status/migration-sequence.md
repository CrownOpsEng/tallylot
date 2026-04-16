---
title: "Migration Sequence"
summary: "Incremental landing and retirement rules for moving from the current bridge to the target pipeline without dual authorities."
doc_type: status
audience: human
owner: repo
status: active
nav_order: 20
---

Use this page to sequence implementation increments without a big-bang refactor.
This document keeps migration rules, cutover expectations, and retirement gates
in one place. It does not re-own target product contracts or recreate roadmap
phase detail.

## Roadmap Ownership

[ROADMAP.md](../../ROADMAP.md) is the only numbered implementation program of
record.

Use this page for:

- migration landing rules
- reader and writer cutover expectations
- bridge retirement rules
- parity and replay gates that must hold before one surface is retired

Do not use this page for:

- competing phase numbers
- alternate phase labels
- duplicate product-contract definitions
- duplicate ontology, support-model, or persistence contracts

## Operating Rules

Every slice must obey the following rules before code lands:

- declare the slice scope
- name the authoritative writer for every affected scope
- name the authoritative reader for every affected consumer
- declare the product ids and upstream product-ref fields used by each target
  kernel the slice introduces
- name the derived compatibility projection for every unmigrated reader
- name any declared compatibility sidecars needed to preserve retained legacy
  fields for those unmigrated readers
- name the cutover gate and retirement gate for every affected bridge surface

Migration-wide rules:

- no consumer may read a bridge surface and a target product as peer
  authorities
- once a target product exists for an in-scope family, that target product is
  the authoritative persisted truth surface for that scope
- bridge surfaces that remain in use after that point are compatibility
  projections only
- unchanged bridge outputs must remain reproducible from the authoritative
  target kernels during the compatibility window

The authoritative cutover matrix lives in
[Bridge To Target Mapping](../concepts/bridge-to-target-mapping.md).

## Landing Order

### 1. Contract Lock

Before broad implementation, freeze:

- target product contracts on
  [Pipeline Stage Contracts](../concepts/pipeline-stage-contracts.md)
- ontology and ref seams on
  [Domain Ontology](../concepts/domain-ontology.md)
- shared blockers, reviews, readiness, and `SubjectRef` rules on
  [Gaps And Readiness](../concepts/gaps-and-readiness.md)
- persistence, partitioning, and fast-path rules on
  [Reconciliation And Tax Architecture](../concepts/reconciliation-tax-architecture.md)
- bridge-to-target cutover rules on
  [Bridge To Target Mapping](../concepts/bridge-to-target-mapping.md)

Broad parallel implementation must not begin before those owner pages are
aligned and frozen.

### 2. First Upstream Slice

Land the current first upstream
[`EvidenceSet -> ClaimSet`](../reference/first-slice-contract.md) slice.

Required posture:

- `EvidenceSet` becomes authoritative for in-scope evidence selection
- `ClaimSet` becomes authoritative for in-scope evidence-local meaning
- `translation_input_plan.json`, `EconomicActivityDraft`, and
  `SourceTranslationBatch` survive only as derived compatibility projections

### 3. First Downstream Slice

Land the current first downstream
[`EconomicFacts -> ReconciliationState -> Checkpoint`](../reference/first-downstream-slice-contract.md)
slice.

Required posture:

- `EconomicFacts` becomes authoritative for in-scope accepted economic meaning
- `ReconciliationState` becomes authoritative for in-scope continuity segments
  and balance targets
- `Checkpoint` becomes authoritative for in-scope accepted checkpoint truth
- `TransactionFact`, `balance_snapshots.csv`, and `balance_references.csv`
  survive only as derived compatibility projections for unmigrated readers

### 4. Reader Cutovers

After those slices land, migrate readers one consumer surface at a time:

- evidence and claim readers move to target kernels first
- reconciliation and checkpoint readers move next
- balance inspect/check/summarize moves only when its application surface is
  explicitly repointed
- accounting and tax readers move only after their upstream products are
  authoritative and stable

### 5. Later Downstream Products

Land `Journal`, `TaxInputs`, and `TaxOutputs` only after the upstream target
products they depend on are authoritative for the relevant scope.

Rules:

- do not let accounting repair economic or checkpoint truth
- do not let tax decide source meaning, reconciliation completeness, or
  checkpoint acceptance

## Bridge Retirement Rules

Retire or demote a bridge surface only when all of the following are true:

- the slice names one authoritative writer for the affected scope
- every active reader has a declared target reader or derived compatibility
  projection
- parity and replay gates for the affected slice pass on unchanged evidence
- current-state docs are updated if the implemented live runtime surface
  changes

Bridge retirement is therefore:

- per scope, not global
- per reader, not just per writer
- controlled by cutover gates, not by naming preference

## Parity And Replay Gates

Do not retire an older path until all relevant gates pass:

- adapter or parser contract tests for the affected slice
- projection parity tests for every retained compatibility surface
- target-kernel replay checks for the authoritative product
- reconciliation or checkpoint parity where the slice reaches those stages
- end-to-end smoke coverage for the affected workflow

When a compatibility projection remains active, parity must prove:

- the projection is reproducible from the authoritative target kernels
- the projection preserves unchanged bridge behavior for unmigrated readers
- the projection does not introduce new authority outside the target kernels

## Docs And Control-Plane Updates

When a migration slice changes architecture ownership or the live runtime
surface, update these pages together:

- [ROADMAP.md](../../ROADMAP.md)
- [Architecture Overview](../concepts/architecture-overview.md)
- [Bridge To Target Mapping](../concepts/bridge-to-target-mapping.md)
- [Current Bridge Contracts](../concepts/current-bridge-contracts.md) if live
  bridge truth changes
- the owning slice reference page if the bounded slice contract changes

Current-state docs stay truthful to implemented behavior. Forward-looking docs
stay detailed enough that later implementation does not need to invent ids,
reader cutovers, storage placement, or support-model boundaries.
