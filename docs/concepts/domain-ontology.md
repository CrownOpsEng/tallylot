---
title: "Domain Ontology"
summary: "Target economic ontology, identity seams, ref recipes, package ownership, and bridge-versus-target modeling rules."
doc_type: concept
audience: human
owner: repo
status: active
naming_scope: forward_target
nav_order: 35
---

Use this page when shaping the target domain model. This page defines the
target ontology, identity seams, ref recipes, and target package ownership.

Current bridge note:

- current bridge code still uses `EconomicActivityDraft`, `TransactionFact`,
  layered bridge classifications, and fact-leg policies
- those bridge contracts remain current-state runtime truth
- this page defines the target ontology that later implementation increments
  should implement directly

## Target Business Concepts

The target model should use these concepts explicitly:

- `Instrument`
- `Location`
- `LegalOwner`
- `BeneficialOwner`
- `Counterparty`
- `Contract`
- `Position`
- `EconomicEvent`
- `EconomicLeg`
- `Valuation`
- `SettlementStatus`
- `LifecycleEvent`
- `AssertionValue`
- `CheckpointAssertion`
- `JournalEntry`
- `Posting`
- `BasisPool`

These are not interchangeable labels. They represent distinct business
concepts, and the model should keep them distinct even when one adapter or one
report happens to collapse them operationally.

## Generic Model Requirements

The target model should remain:

**Current runtime note:** CoinTracking references in this page describe current
adapter-edge or oracle-local truth, not canonical target naming.

- instrument-agnostic
- source-agnostic
- output-agnostic
- storage-neutral

Rules:

- crypto is the current filing scope, not the ontology center
- CoinTracking is an edge import, export, and oracle input, not a runtime
  dependency
- source-specific crypto nouns such as `wallet`, `exchange`, `address`,
  `token`, `chain`, and `tx_hash` may remain in adapter-local,
  source-evidence, compatibility, or current-state surfaces, but the target
  ontology should map those ideas to repo-owned domain nouns such as
  `Location`, `Instrument`, `Position`, or `Contract`
- persistence implements the model; it does not define the model
- no wrapper lanes, compatibility shims, or legacy parallel runtime models
  should survive after a clean replacement is ready
- refactors should replace old structures cleanly when the new structure is
  ready
- tests and parity must be preserved or strengthened through refactors

## Identity And Ref Seams

The target model uses explicit ref seams rather than one generic identity pool.

### Canonical Ref Shapes

| Ref | Meaning | Canonical tuple |
| --- | --- | --- |
| `InstrumentRef` | one resolved instrument identity | `[instrument_id]` |
| `LocationRef` | one resolved location identity | `[location_id]` |
| `LegalOwnerRef` | one resolved legal-owner identity | `[legal_owner_id]` |
| `BeneficialOwnerRef` | one resolved beneficial-owner identity | `[beneficial_owner_id]` |
| `CounterpartyRef` | one resolved counterparty identity | `[counterparty_id]` |
| `ContractRef` | one resolved contract identity | `[contract_kind, legal_owner_ref, beneficial_owner_ref, counterparty_ref, contract_key]` |
| `PositionRef` | one resolved economic position identity | `[beneficial_owner_ref, location_ref, instrument_ref, contract_ref, position_key]` |
| `BasisPoolRef` | one pooled-basis or basis-tracking identity seam | `[tax_policy_id, jurisdiction_or_regime, beneficial_owner_ref, pool_key]` |

Rules:

- do not collapse these refs into one generic id family
- resolve only the identity that the current stage can prove safely
- preserve unresolved identity as explicit blockers instead of guessing across
  seams
- nullable tuple slots keep the base ref name; nullability is part of the
  tuple contract, not the tuple-slot name
- when a stable-id recipe or fingerprint input includes one of these refs, use
  the canonical tuple above rather than an object-name shorthand
- `contract_key` is the stage-owned stable discriminator for one contract
  instance
- `position_key` is the stage-owned stable discriminator for one economic
  exposure or holding state

### `ContractRef` Versus `PositionRef`

Do not collapse `Contract` and `Position`.

- `Contract` is a specific agreement instance with terms, rights, and duties
- `Position` is an economic exposure or holding state that may arise from one
  contract, many contracts, or no explicit contract

Implications:

- business logic should model `Contract` and `Position` explicitly where the
  distinction matters
- shared infrastructure may point at them generically only through the
  `SubjectRef` rules owned by
  [Gap, Review, And Shared Attachment](gaps-and-reviews.md)
- the same shared-infrastructure rule applies when generic attachment is needed
  for `Instrument`, `Location`, ownership identities, counterparties, or
  `CheckpointAssertion`

## Ownership And Counterparty Modeling

Rules:

- beneficial ownership is not interchangeable with legal ownership
- counterparty identity is a separate seam, not an ownership alias
- when an event changes ownership or legal rights in a way that matters later,
  preserve that explicitly rather than hiding it behind a generic transfer
  label
- unresolved ownership transitions should remain visible to reconciliation,
  checkpoint, journal, or tax as appropriate

## `AssertionValue`

`AssertionValue` is the shared value union reused by reconciliation targets,
accepted checkpoints, journal reuse, and downstream tax reasoning.

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
- assertion ids and fingerprints must treat the value variant and its canonical
  content as semantically relevant
- the `AssertionValue` fingerprint uses one UTF-8 JSON array
  `[assertion_value_kind, value_content]`

## `CheckpointAssertion`

`CheckpointAssertion` is the accepted checkpoint-truth concept for one subject
and one as-of point. Persisted kernels carry that concept as
`CheckpointAssertionRecord`.

Rules:

- it is distinct from a reconciliation-stage checkpoint proposal record
- it is distinct from current bridge balance snapshots
- it is distinct from current bridge balance references
- it is distinct from the containing accepted `Checkpoint`
- downstream stages may consume `CheckpointAssertion` truth, but they must not
  redefine them into incompatible local variants
- accepted checkpoint truth should be modeled as `CheckpointAssertion` first
  and checkpoint records second
- `CheckpointAssertion` carries one `AssertionValue`, not one untyped
  convenience
  blob

## Valuation

Valuation is first-class whenever it changes downstream behavior.

Minimum valuation concerns:

- amount
- currency
- purpose
- timestamp
- origin
- confidence
- provenance

### `ValuationPurpose`

Shared vocabulary:

- `economic_measurement`
- `checkpoint_measurement`
- `journal_measurement`
- `tax_measurement`
- `market_measurement`

Rules:

- valuation belongs in the economic model when it changes checkpoint,
  journal, or tax behavior
- valuation purpose must be explicit enough to distinguish economic,
  checkpoint, journal, tax, and market-measurement jobs
- valuation should not be hidden only inside renderer detail or one-off policy
  sidecars
- missing or uncertain valuation should remain explicit when downstream stages
  still need to reason about it

## Instrument Classification

`InstrumentKind` is the shared bounded instrument-classification vocabulary for
target identity and claim contracts.

### `InstrumentKind`

Shared vocabulary:

- `unknown`
- `crypto`
- `fiat`
- `equity`
- `derivative`

Rules:

- `instrument_kind` uses this shared vocabulary when claim or identity
  contracts need a bounded instrument classification
- keep the vocabulary neutral and broad enough to survive beyond the current
  crypto filing scope
- do not mint competing end-state `instrument_class`, `asset_class`, or
  `instrument_type` families for the same concept
- narrower market, venue, or adapter-specific detail belongs in other fields
  such as identifier scheme, venue, or compatibility-local metadata

## Temporal Semantics

Time rules must survive replay, retroactive correction, and cross-stage audit.

Required distinctions:

- `effective_at` expresses when the economic or checkpoint meaning applies
- date-scoped and timestamp-scoped meaning stay distinct in canonical scalar
  form
- `recorded_at` expresses when the system accepted or recorded the later-stage
  truth

Rules:

- `effective_at` and `recorded_at` are not interchangeable
- date-only meaning must remain distinct from exact timestamps
- retroactive corrections emit superseding records with explicit lineage rather
  than mutating prior accepted truth in place
- later stages may compare `effective_at` and `recorded_at`, but they should
  not collapse them into one timeline just to make replay look simpler

## Economic Model

The target economics layer centers on durable economic meaning rather than on
activity-label expansion.

Modeling rules:

- model accepted economic meaning as `EconomicEvent` plus `EconomicLeg`
- keep settlement status, supersession lineage, and lifecycle events explicit instead of
  flattening them into activity labels
- keep valuation first-class when it changes downstream journal,
  checkpoint, or tax behavior
- let ownership and counterparty state remain explicit where known

The target economics layer must be able to express:

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
- one event-kind vocabulary that distinguishes asset movement, cash movement,
  obligations or rights, settlement, collateral, financing, fees or rebates,
  withholding, lifecycle restructure, and correction or supersession behavior
- one stable leg set with signed quantities and explicit leg roles
- explicit effective time in canonical temporal form
- explicit settlement status and lifecycle event where continuity or later treatment
  depends on them
- explicit supersession lineage for corrections instead of in-place mutation
- ownership and counterparty refs where they are known and later stages rely on
  them
- valuation records with explicit purpose where downstream behavior depends on
  them

## `SettlementStatus`

`SettlementStatus` remains first-class whenever completeness, continuity, or
later treatment depends on it.

Shared vocabulary:

- `pending`
- `partial`
- `settled`
- `failed`
- `reversed`
- `unknown`

Rules:

- settlement status should remain explicit where timing, completeness, or
  continuity matters
- settlement status should not be inferred later from one output-specific row
  label when the economic model can carry it directly

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

## Bounded Economics Reconciliation Checkpoint Restriction

The bounded economics/reconciliation/checkpoint contract intentionally uses a
narrow `PositionRef` identity shape for the current held-balance scope.

Slice rule:

- this slice may use only
  `PositionRef = [beneficial_owner_ref, location_ref, instrument_ref, null, "held_position"]`
- `beneficial_owner_ref` must resolve to the filing beneficial owner in scope
- `location_ref` must resolve to the in-scope held location or
  sub-location
- `instrument_ref` must resolve to the in-scope instrument
- `contract_ref` stays `null` in this slice
- later slices may widen `position_key` values and contract participation,
  but they must keep the canonical tuple shape unchanged

## Bridge Classifications Versus Target Ontology

Current bridge classifications remain real and important, but they are not the
center of the long-term model.

Rules:

- bridge classifications stay valid for the current bridge and for current
  renderer hints
- bridge classifications do not define the full ontology
- future support for broader financial instruments should be driven by the
  target ontology, not by endlessly adding new activity labels
- output hints and policy hints remain downstream aids, not the primary
  authority
  of economic truth

Bridge-specific classification rules live in
[Transaction Classification](transaction-classification.md), not here.

## Naming Posture

- keep bridge names in live bridge code until later implementation slices land
- use target ontology names when defining new target-layer concepts in docs and
  later implementation work
- distinguish concept, ref, and record names explicitly:
  `BasisPool` is a concept, `BasisPoolRef` is an identity seam, and
  `*Record` names belong to persisted kernels
- keep `journal` aligned across the end-state stage vocabulary, package roots,
  and product-adjacent prose; reserve `accounting` for broader prose or
  bridge-local hint families
- keep `economics` aligned across stage vocabulary, package roots, and
  product-adjacent prose; reserve `economic` for adjective use inside the
  owned product family such as `EconomicFacts`
- prefer explicit family names such as `gap` and `review`, or explicit
  capability-owned readiness-view names, in forward-looking prose when those
  are the owned surfaces; reserve generic `support` for the intentional shared
  root or bounded field names such as `support_shape`
- avoid umbrella package roots such as `entities/` once the owned identity
  families are already known
- keep singular concept families on singular package stems such as
  `assertion/`
- keep target-layer kind families aligned to the shared domain noun or held
  truth axis. Prefer `contract` over `contract_term`, and kind families such
  as `cash_amount`, `basis_amount`, `owner_state`, and `location_state` over
  mixed or more generic alternates
- do not bake bridge, legacy, current, or compatibility qualifiers into
  target-layer concept names or helper ids unless the name is intentionally
  current-state or adapter-local
- do not force a docs-only bridge rename just to make the target vocabulary
  appear already implemented

## Required Package Ownership

The target package layout follows stage ownership and is not advisory.

**Exception rationale:** `domain/assessment/` stays in this page only as the
shared root for the nested `gap/` and `review/` families plus shared
attachment constructs such as `SubjectRef`. It is not a generic support
catch-all.

**Migration-only root rationale:** `application/compatibility/` remains a
bridge-only migration root for derived compatibility views until those readers
cut over.

Required domain ownership:

- `domain/instrument/`, `domain/location/`, `domain/ownership/`,
  `domain/counterparty/`, `domain/contract/`, and `domain/position/` for
  identity concepts, refs, and stable identity seams
- `domain/evidence/` for evidence members, observations, and selection
  decisions
- `domain/claim/` for claims, claim scopes, claim bundles, and
  claim-bundle decisions
- `domain/economics/` for events, legs, valuations, settlement status, and
  lifecycle events
- `domain/assertion/` for `AssertionValue` and its variants
- `domain/assessment/` as the shared root for nested `gap/` and `review/`
  families plus shared attachment constructs such as `SubjectRef`
- `domain/reconciliation/` for continuity segments, event links, balance
  targets, and checkpoint proposal records
- `domain/checkpoint/` for accepted checkpoint truth
- `domain/journal/` for journal models
- `domain/tax/` for tax inputs, basis transitions, tax-policy contracts,
  tax carry-forward records, tax unsupported-input records, and outputs

Required application ownership:

- `application/intake/` for capture planning and apply
- `application/profiling/` for capture profile construction, inventory
  inspection, and timezone review
- `application/evidence/` for shared statement extraction, evidence selection,
  and provenance locator handling
- `application/claim/` for `ClaimSet` construction from evidence
- `application/economics/` for `EconomicFacts` construction
- `application/compatibility/` for bridge compatibility views only
- `application/normalization/` for current-state migration-era orchestration
  while the live bridge still exists
- `application/reconciliation/` for continuity, linkage, balance target
  evaluation, and checkpoint proposal records
`domain/assessment/` stays generic only because it is the shared root for the
nested `gap/` and `review/` families plus shared attachment constructs such as
`SubjectRef`.
No unrelated family may be added under `domain/assessment/` without a separate
standards decision.
`application/compatibility/` is migration-only and must not become a durable
application center.

- `application/checkpoint/` for `Checkpoint` acceptance, manual assertion
  intake, and opening-state adoption
- `application/journal/` for journal expansion, entry checks, and journal
  views
- `application/tax/` for `TaxInputs` construction, basis transitions, policy
  selection, and `TaxOutputs` generation
- `application/rendering/` for downstream rendering orchestration
- `application/workspace/` for workspace resolution and initialization

Assessment behavior stays in the owning application slice. Shared
`domain/assessment/` contracts and persisted `assessment/gap/`,
`assessment/review/` sidecars do not create a
shared application assessment center.

### Reserved Future Capability Families

Reserve these future application families conceptually, but not as required
package ownership yet:

- application/reporting/ for cross-stage or cross-product reporting
- application/portfolio/ for holdings and portfolio views
- application/visualization/ for charts, dashboards, and visualization
  datasets
- application/investigation/ for drill-down and investigation workflows that
  are not compatibility-only

Rules:

- these families are reserved in prose only until the roadmap trigger ladder
  requires one of them
- do not introduce a generic read-side sink while waiting for a trigger
- do not pre-create all reserved families when only one capability is needed

Boundary rules:

- `application/normalization/` is current-state truth now, but the
  forward-looking target model treats it as migration-era orchestration that
  splits into `evidence`, `claim`, `economics`, and `compatibility`
- `interfaces/` orchestrates services only
- `infrastructure/` implements ports
- `application/` depends on domain and ports
- `domain/` has no infrastructure imports

Implementation-shaping rule:

- use this page plus
  [Economics Reconciliation Checkpoint Contract](../reference/economics-reconciliation-checkpoint-contract.md)
  when choosing where new target-stage work lands
- do not leave package placement to implementation-time judgment once the
  target contract already names the owning stage
- this page defines the required target ownership model; it does not claim the
  current runtime already uses that package layout
