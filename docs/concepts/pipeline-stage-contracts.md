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
- target-product kernel rules in this page are authoritative; other docs may point
  here but should not restate competing kernel, id, or fingerprint contracts

## Handoff Rules

Every stage contract should answer four questions clearly:

- what comes in
- what the stage is allowed to decide
- what comes out
- what remains explicitly unresolved for later stages

Shared rules:

- every output preserves stable ids and enough upstream linkage for later audit
- later stages may add stage-owned sidecars and summaries, but must not
  silently rewrite upstream truth to make their own outputs look tidy
- if a stage cannot support a required decision, it emits explicit blockers,
  unresolved records, or deferred records rather than inventing a fallback
- replay and parity gates operate on kernels first and inspect envelopes
  separately only where the slice requires them

## Shared Product Rules

### Versioning, Serialization, And Fingerprints

- every target product carries a `schema_version`
- readers accept only the declared supported versions for that product
- unknown schema versions fail fast
- compatibility is forward-only by default; do not promise long-lived in-place
  compatibility unless the owning product explicitly declares a narrower window
- regeneration from upstream products or evidence is the normal recovery path
  for incompatible target-stage artifacts
- every target product defines one stable serialization and one stable
  fingerprint over semantically relevant kernel content
- kernel fingerprints use stable UTF-8 JSON serialization with stable object
  key order and declared array order, hashed with SHA-256
- fingerprints include semantically relevant upstream ids or upstream
  fingerprint references plus owning stage decisions
- fingerprints exclude presentation-only formatting noise, explanation text,
  and sidecar payloads that do not change kernel meaning
- sidecars and explanation payloads use their own schema and fingerprint rules
  when they are persisted independently

### Kernel And Envelope Rule

- every target product separates a compact computational kernel from optional
  envelopes or sidecars
- the kernel holds stable ids, ordering keys, owning decisions, and the
  downstream-required references needed for replay and reducers
- the envelope holds provenance detail, explanation, reviews, comparison
  traces, and policy notes
- sidecars must not become the only copy of determinant state or business
  meaning
- any later rehydration path must join through stable ids emitted by the
  kernel

### Shared Kernel Status Vocabulary

Use these bounded status vocabularies across target kernels:

- `selection_status`:
  - `selected`
  - `superseded`
  - `blocked`
- `claim_status`:
  - `asserted`
  - `blocked`
  - `advisory`
  - `superseded`
- `compilation_outcome`:
  - `accepted`
  - `blocked`
  - `deferred`
  - `superseded`
- `reconciliation_status`:
  - `complete`
  - `partial`
  - `blocked`
- `checkpoint_status`:
  - `accepted`
  - `adopted`
  - `blocked`
- `journal_status`:
  - `expanded`
  - `validated`
  - `blocked`
- `tax_status`:
  - `ready`
  - `partial`
  - `blocked`

## `EvidenceSet`

Purpose:

- deterministic intake output before semantic commitment

Owns:

- selected evidence membership
- superseded and blocked alternatives
- deterministic evidence selection decisions
- typed provenance and locator identity for selected evidence
- source-local parsed observations that do not yet require economic meaning

### EvidenceSet Kernel

Kernel fields:

- `evidence_set_id`
- `source`
- `adapter_id`
- `capture_uid`
- `member_id`
- `selection_group_id`
- `observation_id`
- `selection_status`
- `manifest_fingerprint_ref`
- `plan_fingerprint_ref`

### EvidenceSet Envelope

Envelope content may include:

- document metadata
- statement row detail
- inventory detail
- candidate-selection reasoning
- parse diagnostics
- rich provenance payloads

### EvidenceSet Stable Ids

- `evidence_set_id` identifies one bounded evidence emission for one source,
  adapter, capture, and selection-group scope
- `member_id` identifies one selected, superseded, or blocked evidence member
- `observation_id` identifies one typed observation under one evidence member
- `selection_group_id` identifies one deterministic evidence-selection
  decision boundary

### EvidenceSet Ordering

- sort by `source`
- then `capture_uid`
- then `selection_group_id`
- then `selection_status`
- then `member_id`
- then `observation_id`

### EvidenceSet Serialization

- serialize kernel records only
- use stable object-key ordering
- preserve the declared kernel record order above
- represent timestamps and `Decimal` values using the repo's stable string
  forms so the fingerprint is independent of language runtime defaults

### EvidenceSet Fingerprint Inputs

- kernel records in declared order
- `schema_version`
- `manifest_fingerprint_ref`
- `plan_fingerprint_ref`
- selected upstream provenance ids that affect member identity

Handoff to `ClaimSet`:

- `EvidenceSet` provides selected evidence, typed observations, provenance, and
  deterministic selection reasoning
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

### ClaimSet Kernel

Kernel fields:

- `claim_set_id`
- `claim_id`
- `claim_family`
- `claim_status`
- `interpretation_group_id`
- `evidence_member_refs`
- `effective_at`
- `effective_precision`
- `provenance_refs`

### ClaimSet Envelope

Envelope content may include:

- provider-local semantic detail
- comparison traces
- claim explanation
- advisory review payloads
- output-oriented annotations

### ClaimSet Stable Ids

- `claim_set_id` identifies one bounded semantic emission over one evidence set
- `claim_id` identifies one claim family member with one stable semantic role
- `interpretation_group_id` identifies one mutually exclusive claim bundle

### ClaimSet Ordering

- sort by `claim_family`
- then `effective_at` when present
- then `claim_id`
- then `interpretation_group_id`

### ClaimSet Serialization

- serialize kernel records only
- use stable object-key ordering
- preserve the declared claim order above
- include evidence-member refs and provenance refs in sorted order

### ClaimSet Fingerprint Inputs

- kernel records in declared order
- `schema_version`
- `claim_set_id`
- referenced `EvidenceSet` ids or fingerprints
- `interpretation_group_id`

Must guarantee:

- source-local semantics only
- preserved ambiguity where one safe final interpretation is unavailable
- provenance for every claim
- adapters may add provider-local subtyping, but they must preserve the shared
  claim-family distinctions so later compilation remains interoperable

Must not:

- force unresolved meaning into final economic or policy interpretations
- silently discard materially relevant alternative interpretations

### ClaimSet -> EconomicFacts Adjudication

The compiler owns adjudication between `ClaimSet` and `EconomicFacts`.

`InterpretationGroup`:

- one stable `interpretation_group_id`
- one bounded set of mutually exclusive claims or claim bundles
- one status describing whether the group is still unresolved, accepted, or
  blocked
- one shared contract that keeps mutually exclusive meanings explicit instead
  of flattening them into one guessed record

`CompilationDecision`:

- one stable `adjudication_record_id`
- one `compilation_outcome`
- accepted or rejected claim references
- one resolution basis describing why the compiler accepted, deferred, or
  blocked the interpretation group

Adjudication rules:

- interpretation groups are bundle-atomic
- the compiler may accept one whole interpretation group, block one whole
  interpretation group, or defer one whole interpretation group
- partial emission is allowed only across independent interpretation groups
- partial emission is never allowed by accepting only part of one mutually
  dependent group

Handoff to `EconomicFacts`:

- `ClaimSet` hands off source-local assertions, interpretation groups, and
  claim-owned blockers
- the compiler decides which claims can become accepted economic truth and
  which remain blocked, deferred, or superseded

## `EconomicFacts`

Purpose:

- economic truth the system can safely assert

Owns:

- accepted economic meaning
- accepted identity resolution needed for economic truth
- stable economic event and leg structure
- explicit remaining ambiguity that is still economically safe to preserve

### EconomicFacts Kernel

Kernel fields:

- `event_id`
- `event_family`
- `leg_id`
- `accepted_claim_refs`
- `adjudication_record_id`
- `effective_at`
- `effective_precision`
- `recorded_at`
- `settlement_state`
- `lifecycle_state`
- `supersedes_event_id`

### EconomicFacts Envelope

Envelope content may include:

- detailed valuations
- ownership and counterparty context
- explanation of accepted identity seams
- supporting claim traces
- review context carried forward for audit

### EconomicFacts Stable Ids

- `event_id` identifies one accepted economic event
- `leg_id` identifies one stable leg under one accepted event
- `adjudication_record_id` identifies one compiler decision record

### EconomicFacts Ordering

- sort by `effective_at` when present
- otherwise by `recorded_at`
- then `event_id`
- then `leg_id`

### EconomicFacts Serialization

- serialize kernel event records and kernel leg records only
- use stable object-key ordering
- preserve the declared event and leg order above

### EconomicFacts Fingerprint Inputs

- kernel event and leg records in declared order
- `schema_version`
- accepted claim refs
- `adjudication_record_id`
- supersession links

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

- accepted event families stay jurisdiction-neutral and output-neutral
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

### ReconciliationState Kernel

Kernel fields:

- `reconciliation_state_id`
- `continuity_segment_id`
- `link_id`
- `checkpoint_candidate_id`
- `subject_ref`
- `reconciliation_status`
- `balance_target_refs`
- `checkpoint_date`

### ReconciliationState Envelope

Envelope content may include:

- corroboration sidecars
- continuity explanation
- missing-leg detail
- comparison traces
- stage-owned gap and readiness sidecars

### ReconciliationState Stable Ids

- `reconciliation_state_id` identifies one persisted reconciliation product
- `continuity_segment_id` identifies one bounded continuity window
- `link_id` identifies one owned transfer or settlement linkage
- `checkpoint_candidate_id` identifies one reconciliation-owned checkpoint
  proposal

### ReconciliationState Ordering

- sort by `checkpoint_date`
- then `continuity_segment_id`
- then `link_id`
- then `checkpoint_candidate_id`

### ReconciliationState Serialization

- serialize kernel reconciliation records only
- use stable object-key ordering
- preserve the declared reconciliation order above

### ReconciliationState Fingerprint Inputs

- kernel reconciliation records in declared order
- `schema_version`
- referenced `EconomicFacts` ids or fingerprints
- referenced balance-target ids
- referenced checkpoint evidence ids

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

### Checkpoint Kernel

Kernel fields:

- `checkpoint_id`
- `checkpoint_assertion_id`
- `subject_ref`
- `assertion_kind`
- `asserted_as_of_at`
- `accepted_value`
- `trust_level`
- `acceptance_basis`
- `evidence_class`
- `continuity_proof`

### Checkpoint Envelope

Envelope content may include:

- supporting evidence refs
- supporting provenance detail
- continuity explanation
- opening-state adoption detail
- acceptance rationale

### Checkpoint Stable Ids

- `checkpoint_id` identifies one accepted checkpoint container
- `checkpoint_assertion_id` identifies one accepted checkpoint truth record for
  one subject and one as-of point

### Checkpoint Ordering

- sort by `asserted_as_of_at`
- then `subject_ref`
- then `checkpoint_assertion_id`

### Checkpoint Serialization

- serialize kernel checkpoint assertion records only
- use stable object-key ordering
- preserve the declared checkpoint order above

### Checkpoint Fingerprint Inputs

- kernel checkpoint assertion records in declared order
- `schema_version`
- referenced `ReconciliationState` ids or fingerprints
- referenced accepted evidence ids
- referenced opening-state ids when adoption is used

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
- `analysis_ready` may use `operator_assertion` or `partial_continuity`, but
  the lower-trust basis must stay explicit in the accepted checkpoint record
- `operator_only` is required when accepted checkpoint truth relies solely on
  operator assertion without a source-backed evidence class
- `adopted_opening_state` remains a distinct acceptance basis and must preserve
  provenance plus the continuity proof used to roll it into accepted state

Must guarantee:

- accepted checkpoint truth is first-class
- source-backed evidence remains preferred
- operator assertions do not silently become filing-ready checkpoint truth
- adopted opening state remains explicit instead of masquerading as direct
  observation

Must not:

- silently elevate operator convenience inputs into filing-ready truth
- hide the acceptance basis, trust level, or continuity assumptions

Handoff to `Journal` and `TaxInputs`:

- `Checkpoint` provides accepted balances, accepted opening state where used,
  and the acceptance basis
- downstream accounting and tax stages consume that accepted truth rather than
  re-deciding checkpoint trust locally

## `Journal`

Purpose:

- accounting expansion and validation over accepted truth

Owns:

- journal entry and posting expansion
- accounting validation results
- accounting-owned gaps

### Journal Kernel

Kernel fields:

- `journal_id`
- `entry_id`
- `posting_id`
- `economic_event_refs`
- `checkpoint_assertion_refs`
- `journal_status`

### Journal Envelope

Envelope content may include:

- posting explanation
- validation notes
- renderer-facing annotations
- accounting-owned gap sidecars

### Journal Stable Ids

- `journal_id` identifies one accounting emission
- `entry_id` identifies one journal entry
- `posting_id` identifies one posting under one journal entry

### Journal Ordering

- sort by `journal_id`
- then `entry_id`
- then `posting_id`

### Journal Serialization

- serialize kernel journal records only
- use stable object-key ordering
- preserve the declared journal order above

### Journal Fingerprint Inputs

- kernel journal records in declared order
- `schema_version`
- referenced `EconomicFacts` ids
- referenced `Checkpoint` assertion ids

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

### TaxInputs Kernel

Kernel fields:

- `determinant_id`
- `determinant_family`
- `basis_pool_ref`
- `beneficial_owner_ref`
- `instrument_ref`
- `economic_event_refs`
- `checkpoint_assertion_refs`
- `tax_year`

### TaxInputs Envelope

Envelope content may include:

- tax-relevant valuation detail
- supporting ownership and counterparty context
- pool-transition explanation
- tax-owned blocker detail

### TaxInputs Stable Ids

- `determinant_id` identifies one tax determinant
- `basis_pool_ref` identifies one tax basis or pool seam reused across tax years

### TaxInputs Ordering

- sort by `tax_year`
- then `basis_pool_ref`
- then `determinant_family`
- then `determinant_id`

### TaxInputs Serialization

- serialize kernel determinant records only
- use stable object-key ordering
- preserve the declared determinant order above

### TaxInputs Fingerprint Inputs

- kernel determinant records in declared order
- `schema_version`
- referenced `EconomicFacts` ids
- referenced `Checkpoint` assertion ids
- referenced basis-pool ids

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

### TaxOutputs Kernel

Kernel fields:

- `tax_output_id`
- `policy_id`
- `output_family`
- `tax_year`
- `basis_pool_refs`
- `tax_status`

### TaxOutputs Envelope

Envelope content may include:

- policy-specific summaries
- schedules and forms
- carry-forward explanation
- unsupported-coverage notes

### TaxOutputs Stable Ids

- `tax_output_id` identifies one policy-owned output emission

### TaxOutputs Ordering

- sort by `policy_id`
- then `tax_year`
- then `output_family`
- then `tax_output_id`

### TaxOutputs Serialization

- serialize kernel tax-output records only
- use stable object-key ordering
- preserve the declared tax-output order above

### TaxOutputs Fingerprint Inputs

- kernel tax-output records in declared order
- `schema_version`
- referenced `TaxInputs` ids or fingerprints
- selected `policy_id`

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
- [Bridge To Target Mapping](bridge-to-target-mapping.md) for the primary
  current-to-target transformation rules
- [First Slice Contract](../reference/first-slice-contract.md) for the bounded
  Coinbase-first replay and parity contract
- [Domain Ontology](domain-ontology.md) for the target ontology and identity
  seams
- [Gaps And Readiness](gaps-and-readiness.md) for `GapCore`,
  `GapExplanation`, readiness, and `SubjectRef`
- [Reconciliation And Tax Architecture](reconciliation-tax-architecture.md) for
  performance rules, partitioning rules, and filing-critical acceptance
  criteria
