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
  are the live implementation boundary
- that boundary is the current parity baseline
- that boundary is not the final architecture center

Bridge naming rule:

- keep current bridge names in live bridge code until later implementation
  increments replace them
- do not perform large bridge renames as a prerequisite for the next bounded
  architecture increment

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
- [`docs/concepts/bridge-to-target-mapping.md`](../concepts/bridge-to-target-mapping.md)
- [`docs/concepts/pipeline-stage-contracts.md`](../concepts/pipeline-stage-contracts.md)
- [`docs/reference/first-slice-contract.md`](../reference/first-slice-contract.md)
- [`docs/concepts/domain-ontology.md`](../concepts/domain-ontology.md)
- [`docs/concepts/gaps-and-readiness.md`](../concepts/gaps-and-readiness.md)

## Shared Foundations

These foundations are prerequisites, not later cleanup:

- shared stage contracts
- shared ontology and identity boundaries
- shared gap and readiness model
- shared `SubjectRef` rules
- shared checkpoint-assertion direction
- typed tax-policy selection boundary
- target-product versioning, compatibility, serialization, and fingerprint
  rules
- kernel-and-envelope rules with stable rehydration joins
- one primary bridge-to-target mapping for how current adapter outputs map to
  proto-`EvidenceSet` and proto-`ClaimSet`

Rules:

- no stage should invent an incompatible blocker category or readiness model
- no stage should use `SubjectRef` as a substitute for real domain modeling
- no stage should restate the target contracts in a competing document when an
  owning contract page already exists

## Bridge-To-Target Landing Rules

- [Bridge To Target Mapping](../concepts/bridge-to-target-mapping.md) owns the
  live-to-target transformation rules
- [Pipeline Stage Contracts](../concepts/pipeline-stage-contracts.md) owns the
  target product kernels, claim taxonomy, stable ids, ordering, serialization,
  and fingerprint rules
- [First Slice Contract](../reference/first-slice-contract.md) owns the bounded
  Coinbase-first slice, including its replay and parity rules
- broad unified-adapter family migration remains optional prep work, not a
  hidden prerequisite for the first bounded increment

Default first-increment direction:

- use the planner-enabled Coinbase retail export family plus statement-backed
  balance observation flow unless the active filing workspace requires another
  Tier A family to land first
- use [First Slice Contract](../reference/first-slice-contract.md) as the
  bounded default contract for the first increment instead of inferring extra
  adapter inventory
  from the repo

## Phase Order

### Phase 0. Shared Foundations, Contract Lock, And First-Increment Prep

Deliver before broad code changes:

- aligned bridge, target, ontology, and support-model docs
- freeze the detailed contract content on the owning concept and reference
  pages instead of restating those semantics here
- one named first vertical increment with parity and replay gates
- clear bridge-versus-target ownership so later code increments do not re-decide
  naming or stage boundaries

Rules:

- do not start broad tax-engine work before these contracts are written down
- do not let the bridge contract masquerade as the target ontology
- do not make broad unified-adapter family migration a hidden prerequisite for
  the first target-stage increment
- do not start broad target package scaffolding before these contracts are
  frozen on their owner pages

### Phase 1. Formalize `EvidenceSet`

Deliver:

- deterministic selection outputs
- explicit selected, superseded, and blocked evidence outputs
- source-local parsed observation contracts
- a bounded path from current planner artifacts into proto-`EvidenceSet`

Rules:

- evidence selection remains deterministic
- evidence does not force economic meaning
- evidence selection reasoning must survive beyond intake-time heuristics
- the first `EvidenceSet` increment may reuse current adapter boundaries as
  long as the mapping contract is explicit and no second architecture center is
  created

### Phase 2. Introduce `ClaimSet`

Deliver:

- claim-native contracts
- claim-owned issues and reviews
- explicit materially unresolved meaning
- claim-to-economic compilation boundary rules
- one bounded adapter-family path for claim-native output before any broad
  facet migration

Rules:

- ambiguous rows may remain claims without being forced into final economic,
  accounting, or tax meaning
- adapters own source-local meaning only
- the current bridge may remain as a bounded boundary during migration, but it must
  stop forcing final semantics too early
- the first `ClaimSet` increment must not require repo-wide dual-contract support

### Phase 3. Land `EconomicFacts`

Deliver:

- claim-to-economic compilation boundary
- target-directed economic models aligned to the target ontology
- explicit identity, settlement, lifecycle, and valuation handling

Rules:

- no wrapper lane beside the active runtime path
- no bridge rename is required before the first target economic increment lands
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
- exact balance assertions are one reconciliation input, not the whole
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

### Phase 8. Retire Superseded Bridge Outputs And Assumptions

Retire or demote bridge outputs and assumptions only after:

- parity tests exist for the affected increment
- the replacement increment has one active runtime path
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
- later implementation should rename the dev-only shared repo support package area
  from `repo_support/` to `dev_support/`, but this remains future work until
  the corresponding implementation increment lands
- roadmap, migration, and architecture anchors must be updated together when a
  change updates stage ownership, trust-gate sequencing, or shared support
  contracts
