---
title: "Migration Sequence"
summary: "Incremental migration order from the current bridge toward the target stage-first pipeline with parity gates and retirement rules."
doc_type: status
audience: human
owner: repo
status: active
nav_order: 20
---

Use this document to implement the next phase without a big-bang refactor. The
goal is to move from the current bridge into the target pipeline with explicit
parity gates, clean retirement rules, and no wrapper-lane sprawl.

## Migration Objectives

- preserve current working behavior while new foundations land
- avoid freezing the current bridge as the long-term architecture center
- keep adapters and services shippable at every checkpoint
- keep CoinTracking as one edge projection and oracle family, not a migration
  anchor
- preserve current bridge truth while establishing the target stage and
  ontology ownership model

## Current Bridge

Current bridge truth:

- `EconomicActivityDraft`, `TransactionFact`, and the shared balance artifacts
  are the live implementation seam
- that seam is the current parity baseline
- that seam is not the final architecture center

Bridge naming rule:

- keep current bridge names in live bridge code until later implementation
  slices replace them
- do not perform large bridge renames as a prerequisite for the next bounded
  architecture slice

Current live bridge contract owner:

- [`docs/concepts/current-bridge-contracts.md`](../concepts/current-bridge-contracts.md)

## Target Pipeline

The target architecture lands as these final products:

1. `EvidenceSet`
2. `ClaimSet`
3. `EconomicFacts`
4. `ReconciliationState`
5. `Checkpoint`
6. `Journal`
7. `TaxInputs`
8. `TaxOutputs`

Owning contract pages:

- [`docs/concepts/current-bridge-contracts.md`](../concepts/current-bridge-contracts.md)
- [`docs/concepts/pipeline-stage-contracts.md`](../concepts/pipeline-stage-contracts.md)
- [`docs/concepts/domain-ontology.md`](../concepts/domain-ontology.md)
- [`docs/concepts/gaps-and-readiness.md`](../concepts/gaps-and-readiness.md)

## Shared Foundations

These foundations are prerequisites, not later cleanup:

- shared stage contracts
- shared ontology and identity seams
- shared gap and readiness model
- shared `SubjectRef` rules
- shared checkpoint-assertion direction
- typed tax-policy selection seam

Rules:

- no stage should invent an incompatible blocker or readiness surface
- no stage should use `SubjectRef` as a substitute for real domain modeling
- no stage should restate the target contracts in a competing document when an
  owning contract page already exists

## Bridge-To-Target Landing Rules

- `EvidenceSet` formalizes deterministic evidence selection and source-local
  observations now spread across intake, profiling, and translation-input
  planning
- `ClaimSet` becomes the place where `EconomicActivityDraft` responsibilities
  can split into source-local meaning plus preserved ambiguity
- `EconomicFacts` becomes the accepted economic truth that the current
  `TransactionFact` bridge only approximates today
- `ReconciliationState` and `Checkpoint` absorb the trust-gate work currently
  expressed through bridge-era balances, links, and checkpoint scaffolding
- `Journal`, `TaxInputs`, and `TaxOutputs` replace the remaining bridge-era
  tendency to push accounting or tax meaning downward too early

## Phase Order

### Phase 0. Shared Foundations And Schema Lock

Deliver before broad code changes:

- aligned bridge, target, ontology, and support-model docs
- shared provenance, gaps, readiness, checkpoint assertions, identity seams,
  `SubjectRef`, and tax-policy selection contracts
- clear bridge-versus-target ownership so later code slices do not re-decide
  naming or stage boundaries

Rules:

- do not start broad tax-engine work before these contracts are written down
- do not let the bridge contract masquerade as the target ontology

### Phase 1. Formalize `EvidenceSet`

Deliver:

- deterministic selection outputs
- explicit selected, superseded, and blocked evidence outputs
- source-local parsed observation contracts

Rules:

- evidence selection remains deterministic
- evidence does not force economic meaning
- evidence selection reasoning must survive beyond intake-time heuristics

### Phase 2. Introduce `ClaimSet`

Deliver:

- claim-native contracts
- claim-owned issues and reviews
- explicit materially unresolved meaning
- claim-to-economic compilation seam boundaries

Rules:

- ambiguous rows may remain claims without being forced into final economic,
  accounting, or tax meaning
- adapters own source-local meaning only
- the current bridge may remain as a bounded seam during migration, but it must
  stop forcing final semantics too early

### Phase 3. Land `EconomicFacts`

Deliver:

- claim-to-economic compilation seam
- target-directed economic models aligned to the target ontology
- explicit identity, settlement, lifecycle, and valuation handling

Rules:

- no wrapper lane beside the active runtime path
- no bridge rename is required before the first target economic slice lands
- accepted economic meaning should move away from bridge activity-label
  centrality

### Phase 4. Land `ReconciliationState`

Deliver:

- explicit reconciliation completeness and continuity outputs
- target gap and readiness adoption where the owning stage can support it
- transfer linkage, balance targets, and checkpoint candidacy under one
  reconciliation-owned product

Rules:

- reconciliation consumes accepted economic truth plus checkpoint evidence
- exact balance assertions are one reconciliation input surface, not the whole
  reconciliation product

### Phase 5. Land `Checkpoint`

Deliver:

- explicit checkpoint truth and acceptance basis
- source-backed checkpoint evidence requirements
- trust level and adopted opening-state handling
- checkpoint continuity reports

Rules:

- checkpoint truth remains source-backed where filing readiness requires it
- operator-confirmed balances may support runtime progress but do not become
  filing-ready checkpoint truth by default

### Phase 6. Land `Journal`

Deliver:

- internal journal model
- posting expansion and validation
- accounting-owned blockers

Rules:

- accounting validates accepted truth
- accounting does not repair truth

### Phase 7. Land `TaxInputs` And `TaxOutputs`

Deliver:

- `TaxInputs`
- selected tax-policy execution
- year-partitioned carry-forward state
- policy-owned `TaxOutputs`

Rules:

- tax outputs flow from `TaxInputs` through selected tax policies
- tax policy does not decide source meaning, reconciliation truth, or
  checkpoint truth

### Phase 8. Retire Superseded Bridge Surfaces

Retire or demote bridge surfaces only after:

- parity tests exist for the affected slice
- the replacement slice has one active runtime path
- downstream stages no longer depend on the superseded bridge-only assumptions
- current-state docs are updated to reflect the new live truth

## Parity Gates

Do not remove an older path until all relevant gates pass:

- adapter or parser contract tests
- projection parity tests
- reconciliation or checkpoint artifact parity where applicable
- end-to-end smoke workflow for the affected slice
- explicit docs updates so current-state truth and target-state planning remain
  aligned

## Docs And Control-Plane Migration

The docs and control-plane baseline for this migration is:

- target stage contracts, ontology, and gap/readiness ownership are already
  separated into focused concept pages
- current-state docs keep current bridge terms where accuracy requires them
- later implementation should rename the dev-only shared repo support surface
  from `repo_support/` to `dev_support/`, but this remains future work until
  the corresponding implementation slice lands
- roadmap, migration, and architecture anchors must be updated together when a
  slice changes stage ownership, trust-gate sequencing, or shared support
  contracts
