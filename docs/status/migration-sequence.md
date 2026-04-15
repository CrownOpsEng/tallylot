---
title: "Migration Sequence"
summary: "Incremental migration order from the current bridge toward the target stage-first pipeline with parity gates and retirement rules."
doc_type: status
audience: human
owner: repo
status: active
nav_order: 20
---

Use this document to implement the next increment without a big-bang refactor.
The goal is to move from the current bridge into the target pipeline with
explicit parity gates, clean retirement rules, and no wrapper-lane sprawl.

## Roadmap Ownership

`ROADMAP.md` is the only numbered implementation program of record.

Use this page for:

- landing rules for the next increment
- bridge-retirement rules
- parity and replay expectations between increments

Do not use this page for:

- competing phase numbers
- alternate phase labels
- a second copy of roadmap sequencing

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

`EvidenceSet -> ClaimSet -> EconomicFacts -> ReconciliationState -> Checkpoint -> Journal -> TaxInputs -> TaxOutputs`

Owning contract pages:

- [`docs/concepts/current-bridge-contracts.md`](../concepts/current-bridge-contracts.md)
- [`docs/concepts/bridge-to-target-mapping.md`](../concepts/bridge-to-target-mapping.md)
- [`docs/concepts/pipeline-stage-contracts.md`](../concepts/pipeline-stage-contracts.md)
- [`docs/reference/first-slice-contract.md`](../reference/first-slice-contract.md)
- [`docs/reference/first-downstream-slice-contract.md`](../reference/first-downstream-slice-contract.md)
- [`docs/concepts/domain-ontology.md`](../concepts/domain-ontology.md)
- [`docs/concepts/gaps-and-readiness.md`](../concepts/gaps-and-readiness.md)

## Shared Foundations

These foundations are prerequisites, not later cleanup:

- shared stage contracts
- shared ontology and identity boundaries
- shared gap and readiness model
- shared checkpoint-assertion direction
- target-product versioning, serialization, and fingerprint rules
- kernel-and-envelope rules with stable rehydration joins
- one bridge-to-target mapping page that owns how current adapter outputs map
  to proto-`EvidenceSet` and proto-`ClaimSet`
- one bounded downstream slice page that owns the first
  `EconomicFacts -> ReconciliationState -> Checkpoint` consumer path

Rules:

- no stage may invent an incompatible blocker category or readiness model
- no stage may use `SubjectRef` as a substitute for real domain modeling
- no stage may restate target contracts in a competing document when an owning
  contract page already exists

## Bridge-To-Target Landing Rules

- [Bridge To Target Mapping](../concepts/bridge-to-target-mapping.md) owns the
  live-to-target transformation rules
- [Pipeline Stage Contracts](../concepts/pipeline-stage-contracts.md) own the
  target product kernels, record families, stable ids, ordering, serialization,
  and fingerprint rules
- [First Slice Contract](../reference/first-slice-contract.md) owns the bounded
  Coinbase-first `EvidenceSet` and `ClaimSet` landing path
- [First Downstream Slice Contract](../reference/first-downstream-slice-contract.md)
  owns the bounded first `EconomicFacts -> ReconciliationState -> Checkpoint`
  landing path
- broad unified-adapter family migration remains optional prep work, not a
  hidden prerequisite for the first bounded increments

## Contract Lock

Deliver before broad code changes:

- aligned bridge, target, ontology, and support-model docs
- frozen downstream record-family contracts and shared support artifacts
- one named first upstream slice and one named first downstream slice
- clear bridge-versus-target ownership so later code increments do not
  re-decide naming, package placement, or stage boundaries

Rules:

- do not start broad target package scaffolding before these contracts are
  frozen on their owner pages
- do not let the bridge contract masquerade as the target ontology
- do not leave gap ids, readiness ids, checkpoint assertion ids, or downstream
  kernel families to implementation-time judgment

## `EvidenceSet` Increment

Deliver:

- deterministic selection outputs
- explicit selected, superseded, and blocked evidence outputs
- source-local parsed observation contracts
- a bounded path from current planner artifacts into proto-`EvidenceSet`

Rules:

- evidence selection remains deterministic
- evidence does not force economic meaning
- evidence-selection reasoning must survive beyond intake-time heuristics
- the first `EvidenceSet` increment may reuse current adapter boundaries as
  long as the mapping contract is explicit and no second architecture center is
  created

## `ClaimSet` Increment

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
- the current bridge may remain as a bounded boundary during migration, but it
  must stop forcing final semantics too early
- the first `ClaimSet` increment must not require repo-wide dual-contract
  support

## `EconomicFacts` Increment

Deliver:

- target-directed accepted economic truth through `EconomicEventRecord` and
  `EconomicLegRecord`
- frozen `event_family` and `leg_role` vocabularies on the owner page
- claim-to-economic compilation decisions with stable adjudication records

Rules:

- no wrapper lane beside the active runtime path
- no bridge rename is required before the first target economic increment lands
- accepted economic meaning should move away from bridge activity-label
  centrality

## `ReconciliationState` Increment

Deliver:

- explicit `ContinuitySegmentRecord`, `LinkRecord`, `BalanceTargetRecord`, and
  `CheckpointCandidateRecord` contracts
- explicit completeness and continuity outputs
- target gap and readiness adoption where the owning stage can support it

Rules:

- reconciliation consumes accepted economic truth plus checkpoint evidence
- exact balance assertions are one reconciliation input, not the whole
  reconciliation product
- the first downstream slice may keep `LinkRecord` out of scope while the
  remainder of the reconciliation contract is still frozen

## `Checkpoint` Increment

Deliver:

- explicit checkpoint truth and acceptance basis
- source-backed checkpoint evidence requirements
- `CheckpointAssertionValue` plus frozen `assertion_kind` vocabulary
- trust level and adopted opening-state handling
- checkpoint continuity reports

Rules:

- checkpoint truth remains source-backed where filing readiness requires it
- operator-confirmed balances may support runtime progress but do not become
  filing-ready checkpoint truth by default
- the first downstream slice requires statement-backed checkpoint evidence
  rather than operator-only acceptance

## `Journal` Increment

Deliver:

- `JournalEntryRecord`, `PostingRecord`, and `ValidationRecord`
- posting expansion and validation surfaces
- accounting-owned blockers

Rules:

- accounting validates accepted truth
- accounting does not repair truth
- posting determinants required for validation stay in the kernel contract

## `Tax` Increment

Deliver:

- `TaxDeterminantRecord` and `BasisTransitionRecord`
- selected tax-policy execution over `TaxInputs`
- year-partitioned carry-forward state
- `TaxOutputRecord`, `CarryForwardRecord`, and `UnsupportedItemRecord`

Rules:

- tax outputs flow from `TaxInputs` through selected tax policies
- tax policy does not decide source meaning, reconciliation truth, or
  checkpoint truth
- tax determinants keep effective time, quantity, direction, and basis
  transitions in the kernel

## Bridge Retirement

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

- target stage contracts, ontology, and gap/readiness ownership are separated
  into focused owner pages
- current-state docs keep current bridge terms where accuracy requires them
- later implementation should rename the dev-only shared repo support package
  area from `repo_support/` to `dev_support/`, but that remains future work
  until the corresponding implementation increment lands
- roadmap, migration, and architecture anchors are updated together when a
  change updates stage ownership, trust-gate sequencing, or shared support
  contracts
