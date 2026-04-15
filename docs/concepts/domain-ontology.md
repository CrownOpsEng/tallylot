---
title: "Domain Ontology"
summary: "Owning concept page for the target economic ontology, identity boundaries, package direction, and bridge-versus-target modeling rules."
doc_type: concept
audience: human
owner: repo
status: active
nav_order: 35
---

Use this page when shaping the target domain model. This document owns the
target ontology and identity boundaries.

Current bridge note:

- current bridge code still uses `EconomicActivityDraft`, `TransactionFact`,
  layered bridge classifications, and fact-leg policies
- those bridge contracts remain current-state runtime truth
- this page defines the target ontology that later implementation increments should
  grow toward

## Core Business Concepts

The target model should use these concepts explicitly:

- `Instrument`
- `Position`
- `Contract`
- `Location`
- `LegalOwner`
- `BeneficialOwner`
- `Counterparty`
- `EconomicEvent`
- `EconomicLeg`
- `SettlementState`
- `LifecycleEvent`
- `Valuation`
- `CheckpointAssertion`
- `Posting`
- `TaxInput`
- `BasisPoolRef`

These are not interchangeable labels. They represent distinct business
concepts, and the model should keep them distinct even when one adapter or one
report happens to collapse them operationally.

## Generic Core Requirements

The target core should remain:

- instrument-agnostic
- source-agnostic
- output-agnostic
- storage-neutral

Rules:

- crypto is the current filing scope, not the ontology center
- CoinTracking is an edge import, export, and oracle input, not a runtime
  dependency
- persistence implements the model; it does not define the model
- no wrapper lanes, compatibility shims, or legacy parallel runtime models
  should survive after a clean replacement is ready
- refactors should replace old structures cleanly when the new structure is
  ready
- tests and parity must be preserved or strengthened through refactors

## Identity Boundaries

Keep these boundaries separate:

- instrument identity
- contract identity
- position identity
- location identity
- legal owner identity
- beneficial owner identity
- counterparty identity

Rules:

- do not collapse these identities into one generic id family
- resolve only the identity that the current stage can prove safely
- preserve unresolved identity as explicit blockers instead of guessing across
  boundaries

Identity resolution should be incremental and explicit. Earlier stages may know
less than later stages, and that is acceptable as long as uncertainty stays
visible.

## `Contract` Versus `Position`

Do not collapse `Contract` and `Position`.

- `Contract` is a specific agreement instance with terms
- `Position` is an economic exposure or holding state that may arise from one
  contract, many contracts, or no explicit contract

Implication:

- business logic should model `Contract` and `Position` explicitly where the
  distinction matters
- shared infrastructure may reference them generically only through the
  `SubjectRef` rules owned by
  [Gaps And Readiness](gaps-and-readiness.md)
- the same shared-infrastructure rule applies when generic attachment is needed
  for `Instrument`, `Location`, ownership identities, counterparties, or
  `CheckpointAssertion`

## `CheckpointAssertion`

`CheckpointAssertion` is the accepted checkpoint-truth record for one subject
and one as-of point.

Rules:

- it is distinct from a reconciliation `CheckpointCandidate`
- it is distinct from a computed `BalanceSnapshot`
- it is distinct from a raw `BalanceReference`
- it is distinct from the containing accepted `Checkpoint`
- downstream stages may consume checkpoint assertions, but they must not
  redefine them into incompatible local variants
- accepted checkpoint truth should be modeled as checkpoint assertions first
  and checkpoint containers second
- checkpoint assertions carry one `CheckpointAssertionValue`, not one
  untyped convenience payload

## `CheckpointAssertionValue`

`CheckpointAssertionValue` is the target union carried by
`Checkpoint.accepted_value`.

Variants:

- `QuantityValue`
- `MoneyValue`
- `OwnerValue`
- `LocationValue`

Variant rules:

- `QuantityValue` carries one signed quantity plus the subject references needed
  to explain what was measured
- `MoneyValue` carries one monetary amount plus one currency
- `OwnerValue` carries one accepted ownership state over legal-owner,
  beneficial-owner, or counterparty references
- `LocationValue` carries one accepted location state
- the union remains explicit so a later implementation cannot silently use one
  scalar type to stand in for quantity, money, ownership, and location truth
- checkpoint assertion ids and fingerprints must treat the accepted-value
  variant and its canonical content as semantically relevant

## Valuation

Valuation is first-class whenever it changes downstream behavior.

Minimum valuation concerns:

- amount
- currency
- purpose
- timestamp
- precision
- source
- confidence
- provenance

Rules:

- valuation belongs in the economic model when it changes checkpoint,
  accounting, or tax behavior
- valuation purpose should be explicit enough to distinguish checkpoint,
  accounting, tax, and general market-observation use instead of letting one
  valuation silently stand in for another job
- valuation should not be hidden only inside renderer metadata or one-off
  policy blobs
- missing or uncertain valuation should remain explicit when downstream stages
  still need to reason about it

## Temporal Semantics

Time rules must survive replay, retroactive correction, and cross-stage audit.

Required distinctions:

- `effective_at` expresses when the economic or checkpoint meaning applies
- `effective_precision` preserves whether that time is exact or date-scoped
- `recorded_at` expresses when the system accepted or recorded the later-stage
  truth

Rules:

- `effective_at` and `recorded_at` are not interchangeable
- date-only meaning must remain distinct from exact timestamps
- retroactive corrections emit superseding records with explicit lineage rather
  than mutating prior accepted truth in place
- later stages may compare `effective_at` and `recorded_at`, but they should
  not collapse them into one timeline just to make replay look simpler
- earlier accepted records are never rewritten in place; later accepted records
  preserve correction lineage through their own `recorded_at` plus explicit
  supersession references

## Economic Model

The target economic layer centers on durable economic meaning rather than on
activity-label expansion.

Modeling rules:

- model accepted economic meaning as `EconomicEvent` plus `EconomicLeg`
- keep settlement, supersession, and lifecycle state explicit instead of
  flattening them into activity labels
- keep valuation first-class when it changes downstream accounting,
  checkpoint, or tax behavior
- let ownership and counterparty state remain explicit where known

The target economic layer must be able to express:

- holdings movements
- cash movements
- obligations and rights
- settlements
- collateral changes
- financing flows
- fees, rebates, and withholding
- corrections and supersession chains
- corporate actions
- restructurings
- lifecycle-heavy activity

Economic facts should describe what happened economically, not what one export
format calls the row.

Minimum invariant seams:

- one stable event identity
- one event-kind family that distinguishes asset movement, cash movement,
  obligations or rights, settlement, collateral, financing, fees or rebates,
  withholding, lifecycle restructure, and correction or supersession behavior
- one stable leg set with signed quantities and explicit leg roles
- explicit effective time and temporal precision when exact timing is not known
- explicit settlement and lifecycle state where continuity or later treatment
  depends on them
- explicit supersession lineage for corrections instead of in-place mutation
- ownership and counterparty references where they are known and later stages
  rely on them
- valuation records with explicit purpose where downstream behavior depends on
  them

## Ownership And Counterparty Modeling

Rules:

- beneficial ownership is not interchangeable with legal ownership
- counterparty identity is a separate seam, not an ownership alias
- when an event changes ownership or legal rights in a way that matters later,
  preserve that explicitly rather than hiding it behind a generic transfer
  label
- unresolved ownership transitions should remain visible to reconciliation,
  checkpoint, accounting, or tax as appropriate

## `SettlementState`

`SettlementState` remains first-class whenever completeness, continuity, or
later treatment depends on it.

Shared vocabulary:

- `pending`
- `partial`
- `settled`
- `failed`
- `reversed`
- `unknown`

Rules:

- settlement state should remain explicit where timing, completeness, or
  continuity matters
- settlement state should not be inferred later from one output-specific row
  label when the economic model can carry it directly

Allowed transitions:

| Current state | Allowed next states | Terminal |
| --- | --- | --- |
| `unknown` | `pending`, `partial`, `settled`, `failed`, `reversed` | no |
| `pending` | `partial`, `settled`, `failed`, `reversed` | no |
| `partial` | `settled`, `failed`, `reversed` | no |
| `settled` | `reversed` | no |
| `failed` | none | yes |
| `reversed` | none | yes |

Rules:

- accepted state must move only through the transitions above
- `failed` and `reversed` are terminal settlement states for one accepted
  event chain

## `LifecycleEvent`

`LifecycleEvent` remains first-class whenever restructurings, migrations,
rolls, term changes, or supersession chains affect later reasoning.

Shared vocabulary:

- `created`
- `amended`
- `migrated`
- `rolled`
- `restructured`
- `terminated`
- `superseded`

Rules:

- lifecycle changes should not be flattened into generic trade-like labels
- corrections should preserve supersession lineage instead of mutating earlier
  accepted meaning in place
- lifecycle events belong in the target economic model, not only in adapter
  annotations or tax-policy notes

Allowed transitions:

| Current lifecycle state | Allowed next states | Terminal |
| --- | --- | --- |
| `created` | `amended`, `migrated`, `rolled`, `restructured`, `terminated`, `superseded` | no |
| `amended` | `amended`, `migrated`, `rolled`, `restructured`, `terminated`, `superseded` | no |
| `migrated` | `amended`, `rolled`, `restructured`, `terminated`, `superseded` | no |
| `rolled` | `amended`, `rolled`, `restructured`, `terminated`, `superseded` | no |
| `restructured` | `amended`, `migrated`, `rolled`, `restructured`, `terminated`, `superseded` | no |
| `terminated` | none | yes |
| `superseded` | none | yes |

Rules:

- accepted lifecycle state must move only through the transitions above
- `terminated` and `superseded` are terminal lifecycle states for one accepted
  chain

## Basis Pool

`BasisPoolRef` is the shared identity seam for pooled-basis or basis-tracking
state reused by tax inputs and policy execution.

Minimum key dimensions:

- tax policy
- jurisdiction or regime
- beneficial owner
- pool scope

Rules:

- basis pools are first-class domain seams, not renderer metadata
- reconciliation and checkpoint stages may reference basis-relevant state, but
  tax owns basis-pool transitions and treatment
- pooled-basis jurisdictions must not force each stage to invent its own pool
  identity model
- `BasisPoolRef` serializes and sorts as
  `[tax_policy_id, jurisdiction_or_regime, beneficial_owner_ref, pool_scope]`

## Bridge Classifications Versus Target Ontology

Current bridge classifications remain real and important, but they are not the
center of the long-term model.

Rules:

- bridge classifications stay valid for the current bridge and for current
  renderer hints
- bridge classifications do not define the full ontology
- future support for broader financial instruments should be driven by the core
  ontology, not by endlessly adding new activity labels
- output hints and policy hints remain downstream aids, not the primary source
  of economic truth

## Neutral Export Surface

The target-neutral domain API should not be inferred from the current bridge
export surface.

Rules:

- the root `domain` export surface is current-state convenience, not target API
  precedent
- current bridge-era helpers such as `asset_claim()` are crypto-oriented
  identity conveniences, not the intended neutral ontology center
- later target package exports should follow stage and ontology ownership, not
  the current bridge-era convenience surface
- do not treat bridge-era crypto helpers as a reason to shape new core models
  around crypto-first assumptions

Bridge-specific classification rules live in
[Transaction Classification](transaction-classification.md), not here.

## Naming Posture

- keep bridge names in live bridge code until later implementation slices land
- use target ontology names when defining new target-layer concepts in docs
  and later implementation work
- do not force a docs-only bridge rename just to make the target vocabulary
  appear already implemented

## Required Package Ownership

The target package layout follows stage ownership and is not advisory.

Required domain ownership:

- `domain/evidence/` for evidence-member identity, typed observations, and
  other source-local evidence concepts
- `domain/claims/` for source-local claim types and interpretation-group
  semantics
- `domain/economics/` for economic events, economic legs, valuations,
  settlement state, and lifecycle state
- `domain/reconciliation/` for continuity segments, link state, balance
  targets, readiness reducers, and checkpoint candidacy
- `domain/checkpoints/` for accepted checkpoint truth, checkpoint assertions,
  and `CheckpointAssertionValue`
- `domain/accounting/` for journals, entries, postings, and validation outputs
- `domain/tax/` for tax determinants, basis transitions, tax-policy contracts,
  carry-forward state, and outputs

Required application ownership:

- `application/intake/` for capture planning and apply
- `application/evidence/` for shared statement extraction, evidence selection,
  and provenance locator handling
- `application/profiling/` for capture profile construction, inventory
  inspection, and timezone review
- `application/normalization/` for evidence-to-claim translation planning and
  current bridge artifact production
- `application/normalization/assembly/` for deterministic merge of accepted
  capture outputs into assembled source datasets
- `application/reconciliation/` for continuity, linkage, balance-target
  evaluation, readiness reducers, and checkpoint candidates
- `application/checkpoints/` for checkpoint evidence assembly, manual balance
  submission validation, and checkpoint acceptance
- `application/accounting/` for journal expansion, validation, and summaries
- `application/tax/` for tax-input assembly, basis transitions, policy
  selection, and tax-output rendering
- `application/outputs/` for downstream renderer orchestration

Boundary rules:

- `interfaces/` orchestrates services only
- `infrastructure/` implements ports
- `application/` depends on domain and ports
- `domain/` has no infrastructure imports

Implementation-shaping rule:

- use this page plus
  [First Downstream Slice Contract](../reference/first-downstream-slice-contract.md)
  when choosing where new target-stage work lands
- do not leave package placement to drafting-time judgment once the target
  contract already names the owning stage
- this page defines the required target ownership model; it does not claim the
  current runtime already uses that package layout
