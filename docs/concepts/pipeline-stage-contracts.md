---
title: "Pipeline Stage Contracts"
summary: "Owning contract for the target pipeline products, stage responsibilities, handoff guarantees, and downstream decision boundaries."
doc_type: concept
audience: human
owner: repo
status: active
nav_order: 25
---

Use this page when defining the target pipeline products or deciding which
stage owns a decision. This document owns the target stage contracts.

Current runtime note:

- the live runtime still centers on `EconomicActivityDraft`,
  `TransactionFact`, `balance_snapshots.csv`, and `balance_references.csv`
- those bridge products remain current-state truth until later implementation
  slices replace them
- this page defines the target stage contracts, not the claim that the current
  code already implements them

The target runtime pipeline is:

`EvidenceSet -> ClaimSet -> EconomicFacts -> ReconciliationState -> Checkpoint -> Journal -> TaxInputs -> TaxOutputs`

## Stage Rules

- upstream stages preserve optionality that they do not own
- downstream stages force specificity only when they own the decision
- no stage may guess a later-stage answer
- no stage may suppress uncertainty that a later stage must still see
- no stage may duplicate upstream semantic payloads unless the meaning has
  changed

## Handoff Rules

Every stage contract should answer four questions clearly:

- what comes in
- what the stage is allowed to decide
- what comes out
- what remains explicitly unresolved for later stages

Shared rules:

- every output must preserve stable ids and enough provenance linkage for later
  audit
- a later stage may add stage-owned sidecars and summaries, but it should not
  silently rewrite upstream truth just to make its own outputs look tidy
- if a stage cannot support a required decision, it should emit explicit
  blockers or unresolved records rather than inventing a one-off fallback lane
- stage contracts should stay compact enough for deterministic replay and
  partitioned recomputation

## Shared Product Rules

### Versioning, Serialization, And Fingerprints

- every target product carries a `schema_version`
- readers accept only the declared supported versions for that product
- unknown schema versions fail fast
- compatibility is forward-only by default; do not promise long-lived in-place
  compatibility unless the owning product explicitly declares a narrower
  compatibility window
- regeneration from upstream products or evidence is the normal recovery path
  for incompatible target-stage artifacts
- every target product defines one canonical serialization and one stable
  fingerprint over semantically relevant content
- fingerprints include semantically relevant upstream references and owning
  decisions, but exclude presentation-only formatting noise and derived
  explanation payloads that do not change kernel meaning
- sidecars and explanation payloads use their own schema and fingerprint rules
  when persisted independently
- presentation-only formatting or ordering noise must not affect fingerprints

### Kernel And Envelope Rule

- every target product separates a compact computational kernel from optional
  envelopes or sidecars
- the kernel holds stable ids, ordering keys, owning decisions, and the
  downstream-required references needed for replay and reducers
- envelopes and sidecars hold provenance detail, explanation, reviews,
  comparison traces, and policy notes
- any later rehydration path must join through stable ids emitted by the kernel
- sidecars must not become the only copy of business meaning or determinant
  state
- replay and parity gates operate on kernels first and inspect envelopes
  separately when the slice requires them

## `EvidenceSet`

Purpose:

- deterministic intake output before semantic commitment

Owns:

- selected evidence membership
- superseded and blocked alternatives
- deterministic evidence selection decisions
- typed provenance and locator identity for selected evidence
- source-local parsed observations that do not yet require economic meaning

Carries:

- selected source artifacts
- source-local parsed observations
- provenance
- document, statement, and inventory observations
- selected, superseded, and blocked alternatives
- deterministic selection decisions

Must guarantee:

- deterministic selection
- stable provenance and locators
- no forced economic meaning
- no forced reconciliation, accounting, or tax decisions

Must not:

- invent economic or policy meaning
- hide file-winner logic inside adapter-local heuristics

Handoff to `ClaimSet`:

- `EvidenceSet` provides selected evidence, typed observations, provenance, and
  selection reasoning
- it does not provide final economic interpretation, final ownership meaning,
  checkpoint acceptance, journal logic, or tax treatment

## `ClaimSet`

Purpose:

- source-local meaning layer before economic truth is fixed

Owns:

- source-local semantic assertions derived from evidence
- explicitly unresolved meaning when one safe final interpretation is not yet
  available
- claim-owned issues and reviews

Carries:

- activity claims
- balance observation claims
- ownership claims
- location claims
- instrument claims
- contract claims
- valuation claims
- candidate interpretations
- claim-owned issues and reviews

Minimum claim-family distinctions:

- `ActivityClaim`
- `BalanceObservationClaim`
- `OwnershipClaim`
- `LocationClaim`
- `InstrumentIdentityClaim`
- `ContractTermClaim`
- `ValuationClaim`
- `ProjectionAnnotation`
- blocking issue and review candidate surfaces

Must guarantee:

- source-local semantics only
- preserved ambiguity where one safe final interpretation is unavailable
- provenance for every claim
- adapters may add provider-local subtyping, but they must preserve the shared
  claim-family distinctions above so later compilation is interoperable

Must not:

- force unresolved meaning into final economic or policy interpretations
- silently discard materially relevant alternative interpretations

Handoff to `EconomicFacts`:

- `ClaimSet` hands off source-local assertions and explicitly unresolved
  branches
- the compiler is responsible for deciding which claims can become accepted
  economic truth and which must remain blocked or unresolved

## `EconomicFacts`

Purpose:

- economic truth the system can safely assert

Owns:

- accepted economic meaning
- accepted identity resolution needed for economic truth
- stable economic event and leg structure
- explicit remaining ambiguity that is still economically safe to preserve

Carries:

- economic events
- economic legs
- instrument identity
- contract identity where relevant
- position identity where relevant
- owner and counterparty identity where known
- temporal precision
- settlement and supersession links
- valuations
- confidence and ambiguity markers

Minimum accepted economic determinants:

- stable event identity and event-kind family
- effective time and temporal precision
- one stable leg set with signed quantities and explicit leg roles
- settlement state where later stages depend on it
- lifecycle state where later stages depend on it
- supersession or correction lineage
- ownership and counterparty references where known
- valuation records with explicit purpose where downstream behavior depends on
  them
- stable references back to accepted upstream claims

Must support:

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

Rules:

- accepted event kinds stay jurisdiction-neutral and output-neutral
- corrections preserve supersession lineage instead of mutating accepted
  economic truth in place
- unresolved economic detail may remain explicit only where later stages can
  still reason safely from the accepted kernel

Must not:

- collapse to spot-trade assumptions
- let output hints drive core behavior

Handoff to `ReconciliationState`:

- `EconomicFacts` provides accepted economic events, legs, identity seams,
  settlement links, lifecycle state, and valuations where they are already safe
- it does not claim that continuity is complete, transfers are fully linked, or
  checkpoint truth is accepted

## `ReconciliationState`

Purpose:

- completeness, linkage, continuity, checkpoint candidates, and
  reconciliation-owned blockers

Owns:

- transfer and settlement linkage
- continuity decisions
- balance targets and assertion outcomes
- reconciliation-owned gaps and readiness
- checkpoint candidacy derived from reconciled economics plus checkpoint
  evidence

Carries:

- transfer links
- balance targets and assertions
- continuity windows
- missing funding and settlement legs
- unresolved ownership transitions
- corroboration sidecars
- checkpoint candidates
- reconciliation-owned gaps
- readiness records

Must guarantee:

- explicit completeness decisions
- explicit continuity decisions
- explicit missing-leg and missing-evidence surfaces
- preservation of partial truth when the whole window is not yet clean
- no rewriting of upstream truth to satisfy checks

Must not:

- reclassify upstream economics to make continuity easier
- bury missing evidence inside whole-dataset summaries

Handoff to `Checkpoint`:

- `ReconciliationState` provides checkpoint candidates, corroboration,
  continuity outcomes, and reconciliation-owned blockers
- checkpoint acceptance still belongs to the checkpoint stage

## `Checkpoint`

Purpose:

- accepted checkpoint truth and acceptance basis

Owns:

- accepted checkpoint assertions
- adopted opening state when intentionally used
- acceptance basis, trust level, and continuity into accepted state

Carries:

- accepted checkpoint assertions
- adopted opening state when intentionally used
- supporting evidence and provenance
- continuity decisions into accepted state
- trust level and acceptance basis

Controlled checkpoint vocabularies:

- `trust_level`:
  - `filing_ready`
  - `analysis_ready`
  - `operator_only`
- `acceptance_basis`:
  - `source_document`
  - `source_system_balance`
  - `reconciled_continuity`
  - `adopted_opening_state`
  - `operator_assertion`
- `evidence_class`:
  - `statement_balance`
  - `platform_balance`
  - `wallet_snapshot`
  - `inventory_proof`
  - `operator_assertion`
- `continuity_proof`:
  - `direct_observation`
  - `reconciled_rollforward`
  - `opening_state_rollforward`
  - `partial_continuity`

Minimum admissibility rules:

- `filing_ready` requires:
  - `acceptance_basis` other than `operator_assertion`
  - `evidence_class` other than `operator_assertion`
  - `continuity_proof` other than `partial_continuity`
- `analysis_ready` may use `operator_assertion` or `partial_continuity`, but the
  lower-trust basis must stay explicit in the accepted checkpoint record
- `operator_only` is required when accepted checkpoint truth relies solely on
  operator assertion without a source-backed evidence class
- `adopted_opening_state` remains a distinct acceptance basis and must preserve
  provenance plus the continuity proof used to roll it into accepted state

Must guarantee:

- accepted checkpoint truth is first-class
- source-backed evidence remains preferred
- operator assertions do not silently become filing-ready checkpoint truth
- `filing_ready` checkpoint truth must not rely solely on `operator_assertion`
  acceptance
- adopted opening state remains explicit instead of masquerading as direct
  observation

Must not:

- silently elevate operator convenience inputs into filing-ready truth
- hide the acceptance basis, trust level, or continuity assumptions

Handoff to `Journal` and `TaxInputs`:

- `Checkpoint` provides accepted balances, accepted opening state where used,
  and the acceptance basis
- downstream accounting and tax stages must consume that accepted truth rather
  than re-deciding checkpoint trust locally

## `Journal`

Purpose:

- accounting expansion and validation over accepted truth

Owns:

- journal entry and posting expansion
- accounting validation results
- accounting-owned gaps

Carries:

- journal entries and postings
- provenance back to accepted upstream truth
- validation results
- accounting-owned gaps

Must guarantee:

- deterministic posting expansion
- explicit validation
- explicit unsupported accounting coverage

Must not:

- become a truth repair layer

Handoff to downstream renderers:

- `Journal` provides accounting-owned postings, validation results, and
  accounting-owned blockers
- renderer-specific row shapes stay at output boundaries rather than becoming
  part of the shared journal contract

## `TaxInputs`

Purpose:

- policy-ready, jurisdiction-neutral tax input surface

Owns:

- tax determinants derived from reconciled economics plus accepted checkpoint
  truth
- explicit tax-owned blockers where upstream truth is still not tax-complete

Carries:

- acquisitions
- dispositions
- income events
- financing costs
- internal transfers
- corporate actions
- tax-relevant valuations
- basis or pool state transitions
- tax-owned unresolved items

Minimum determinant families:

- `acquisition`
- `disposition`
- `income`
- `expense_or_fee`
- `financing_cost`
- `internal_transfer`
- `basis_adjustment`
- `corporate_action`

Each determinant preserves, where applicable:

- stable determinant identity
- determinant family
- effective time and temporal precision
- instrument, pool, or other affected subject reference
- quantity and direction
- tax-relevant valuation
- ownership or counterparty references
- upstream economic-event references
- accepted checkpoint or opening-state references when tax basis depends on them
- basis or pool transition references

Must guarantee:

- jurisdiction-neutral determinants
- explicit basis-affecting state changes
- explicit tax-owned blockers where upstream truth is not tax-complete
- tax-incomplete items stay explicit instead of being upgraded into guessed
  treatment

Must not:

- embed one jurisdiction's output schema
- decide source meaning, reconciliation truth, checkpoint truth, or accounting
  truth

Handoff to `TaxOutputs`:

- `TaxInputs` provides the determinant surface that selected policies operate
  on
- the policy layer decides treatment and output shape, not the upstream claim,
  economic, or reconciliation layers

## `TaxOutputs`

Purpose:

- one selected tax policy's outputs

Owns:

- policy-specific summaries, forms, schedules, and carry-forward state
- tax-policy explanations, limitations, and unsupported outputs
- tax-owned blockers that survive policy execution

Carries:

- summaries
- forms and schedules
- carry-forward state
- unsupported or deferred outputs
- policy-specific notes

Must guarantee:

- outputs are derived from `TaxInputs` through selected tax policies
- policy selection is explicit
- unsupported coverage stays explicit instead of being silently omitted

Must not:

- claim to come directly from `EconomicFacts` or `ReconciliationState`
- backfill earlier-stage semantic gaps by guessing

## Shared Contract References

The pipeline products rely on shared supporting contracts defined elsewhere:

- [Current Bridge Contracts](current-bridge-contracts.md) for the live bridge
  runtime truth
- [Domain Ontology](domain-ontology.md) for the target ontology and identity
  seams
- [Gaps And Readiness](gaps-and-readiness.md) for `GapCore`,
  `GapExplanation`, readiness, and `SubjectRef`
- [Reconciliation And Tax Architecture](reconciliation-tax-architecture.md) for
  performance rules, tax-policy architecture, and filing-critical acceptance
  criteria
