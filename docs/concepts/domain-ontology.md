---
title: "Domain Ontology"
summary: "Owning concept page for the target economic ontology, identity seams, package direction, and bridge-versus-target modeling rules."
doc_type: concept
audience: human
owner: repo
status: active
nav_order: 35
---

Use this page when shaping the target domain model. This document owns the
target ontology and identity seams.

Current bridge note:

- current bridge code still uses `EconomicActivityDraft`, `TransactionFact`,
  layered bridge classifications, and fact-leg policies
- those bridge contracts remain current-state runtime truth
- this page defines the target ontology that later implementation slices should
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

These are not interchangeable labels. They represent distinct business
concepts, and the model should keep them distinct even when one adapter or one
reporting surface happens to collapse them operationally.

## Generic Core Requirements

The target core should remain:

- instrument-agnostic
- source-agnostic
- output-agnostic
- storage-neutral

Rules:

- crypto is the current filing scope, not the ontology center
- CoinTracking is an edge import, export, and oracle surface, not a runtime
  dependency
- persistence implements the model; it does not define the model
- no wrapper lanes, compatibility shims, or legacy parallel runtime models
  should survive after a clean replacement is ready
- refactors should replace old structures cleanly when the new structure is
  ready
- tests and parity must be preserved or strengthened through refactors

## Identity Seams

Keep these seams separate:

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
  seams

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

## Settlement And Lifecycle State

Rules:

- settlement state should remain explicit where timing, completeness, or
  continuity matters
- lifecycle changes such as restructurings, migrations, contract rolls, and
  supersession chains should not be flattened into generic trade-like labels
- corrections should preserve supersession lineage instead of mutating earlier
  accepted meaning in place

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

Bridge-specific classification rules live in
[Transaction Classification](transaction-classification.md), not here.

## Naming Posture

- keep bridge names in live bridge code until later implementation slices land
- use target ontology names when defining new target-layer concepts in docs
  and later implementation work
- do not force a docs-only bridge rename just to make the target vocabulary
  appear already implemented

## Package Direction

The target package direction should follow the ontology and stage ownership:

- `domain/claims/` for source-local claim types
- `domain/economics/` for economic events, legs, valuations, settlement, and
  lifecycle state
- `domain/reconciliation/` for continuity, linkage, readiness, and checkpoint
  candidacy
- `domain/checkpoints/` for accepted checkpoint truth and checkpoint
  assertions
- `domain/accounting/` for journals, entries, postings, and validation outputs
- `domain/tax/` for tax inputs, policy contracts, carry-forward state, and
  outputs

Suggested application ownership:

- `application/intake/` for capture planning, apply, and evidence selection
- `application/evidence/` for shared statement extraction and provenance
  locator handling
- `application/profiling/` for capture profile construction, inventory
  inspection, and timezone review
- `application/normalization/` for evidence-to-claim translation planning and
  current bridge artifact production
- `application/normalization/assembly/` for deterministic merge of accepted
  capture outputs into assembled source datasets
- `application/reconciliation/` for links, continuity, readiness reducers, and
  checkpoint candidates
- `application/checkpoints/` for checkpoint evidence assembly, manual balance
  submission validation, and checkpoint acceptance
- `application/accounting/` for journal expansion, validation, and summaries
- `application/tax/` for tax-input assembly, policy selection, and tax-output
  rendering
- `application/outputs/` for downstream renderer orchestration

Boundary rules:

- `interfaces/` orchestrates services only
- `infrastructure/` implements ports
- `application/` depends on domain and ports
- `domain/` has no infrastructure imports

This is target direction only. It does not claim the current runtime already
uses that package layout.
