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
- no stage may duplicate upstream meaning unless the downstream-owned meaning
  has changed
- target-product kernel rules in this page are authoritative; other docs may
  point here but should not restate competing kernel, id, fingerprint, or
  sidecar contracts

## Handoff Rules

Every stage contract answers four questions:

- what comes in
- what the stage may decide
- what comes out
- what remains explicitly unresolved for later stages

Shared rules:

- every output preserves stable ids and enough upstream linkage for later audit
- later stages may add stage-owned sidecars and summaries, but must not
  silently rewrite upstream truth to make their own outputs look tidy
- if a stage cannot support a required decision, it emits explicit blockers,
  unresolved records, or deferred records rather than inventing a fallback
- replay and parity gates operate on kernels first and inspect sidecars
  separately only where the slice requires them

## Shared Product Rules

### Versioning, Serialization, And Fingerprints

- every target product carries a `schema_version`
- every target product defines one stable serialization and one stable
  fingerprint over semantically relevant kernel content
- kernel fingerprints use stable UTF-8 JSON serialization with stable object
  key order and declared array order, hashed with SHA-256
- fingerprints include semantically relevant upstream ids or upstream
  fingerprint references plus owning-stage decisions
- fingerprints exclude presentation-only formatting noise, explanation text,
  comparison traces, and sidecars that do not change kernel meaning
- compatibility is forward-only by default; regeneration from upstream products
  or evidence is the normal recovery path for incompatible persisted files

### Stable Id Format

- every stable id defined on this page uses the format
  `<kind>:<sha256(lowercase-hex)>`
- the hash input is one UTF-8 JSON array in declared component order
- component arrays use the owning product's canonical scalar forms exactly as
  emitted; do not add hidden trimming, lowercasing, or resorting outside the
  declared tuple rules

### Product Id And Upstream Ref Rules

- every target product carries one product id in product metadata
- `EvidenceSet` and `ClaimSet` keep `evidence_set_id` and `claim_set_id` as
  their product ids
- later products use dedicated product ids:
  `economic_facts_id`, `reconciliation_state_id`, `checkpoint_id`,
  `journal_id`, `tax_inputs_id`, and `tax_outputs_id`
- upstream product metadata refs use product ids only; they never use
  `kernel_scope_id` or a raw kernel fingerprint
- ordered metadata fields such as `claim_set_refs`,
  `reconciliation_state_refs`, and `economic_facts_refs` sort
  lexicographically by product id unless the owning product declares a
  stronger canonical order
- `kernel_scope_id` remains a derived shared-support and reporting attachment
  only;
  it is not a product id or upstream product ref

### Record Reference Rule

- when a kernel field name ends with `_ref`, `_refs`, or `_id` and the
  stem names one target product owned on this page, the field uses that
  product's metadata id or ordered product-id list
- when a kernel field name ends with `_ref`, `_refs`, or `_id` and the
  stem names one target record family owned on this page, the field uses that
  record family's stable id or ordered stable-id list
- helper tuple refs such as `SubjectRef`, `BasisPoolRef`,
  `AccountRef`, `CommodityRef`, and `OriginRef` remain
  owned by their helper pages and are called out explicitly where used

### Composite Tuple Rules

- `SubjectRef` serializes and sorts as `[subject_kind, subject_id]`
- `BasisPoolRef` serializes and sorts as
  `[tax_policy_id, jurisdiction_or_regime, beneficial_owner_ref, pool_key]`
- when one stable-id recipe, ordering rule, or fingerprint input includes a
  domain ref whose canonical tuple is owned by
  [Domain Ontology](domain-ontology.md), use that tuple form rather than an
  object-name shorthand

### Temporal Scalar Rule

- where a field or id recipe uses a temporal scalar such as `effective_at`,
  `as_of`, or `valued_at`, the
  canonical serialized form must preserve whether the meaning is date-scoped
  or timestamp-scoped
- stages may carry an additional precision field when that stage needs it
  operationally, but the stable id and fingerprint use the canonical temporal
  scalar only once
- nullable fields keep the same canonical field name as the non-null case;
  optionality belongs in the field contract, not the field name

### Kernel And Sidecar Rule

- every target product separates a compact computational kernel from optional
  sidecars
- the kernel holds stable ids, ordering keys, owning decisions, and the
  downstream-required references needed for replay and reducers
- sidecars hold provenance detail, explanation, reviews, comparison traces,
  policy notes, and other non-kernel detail
- sidecars must not become the only copy of required state or business
  meaning
- any later rehydration path must join through stable ids emitted by the
  kernel

### Kernel-Scope Id And Sidecar Attachment

- every target product has one canonical kernel fingerprint
- the shared `kernel_scope_id` contract is owned by
  [Gaps And Readiness](gaps-and-readiness.md)
- `kernel_scope_id` is derived from the emitted kernel fingerprint after
  canonical
  fingerprinting; it is not part of kernel metadata or fingerprint inputs
- `kernel_scope_id` is the product-scope attachment id for readiness,
  comparison, and other shared sidecars when no narrower truthful scope exists
- `kernel_scope_id` is not a substitute for a narrower record id or stage-owned
  scope such as `selection_id`, `claim_scope_id`, `continuity_segment_id`,
  `balance_target_id`, or `checkpoint_proposal_id`

### Shared Record Status And Outcome Vocabulary

Use these bounded record-local vocabularies across target kernels:

- `EvidenceMemberRecord.status`:
  - `selected`
  - `superseded`
  - `blocked`
- `ClaimRecord.status`:
  - `asserted`
  - `superseded`
- `BundleDecisionRecord.outcome`:
  - `accepted`
  - `blocked`
  - `deferred`
  - `superseded`
- `ContinuitySegmentRecord.status`:
  - `complete`
  - `partial`
  - `blocked`
- `JournalEntryRecord.status`:
  - `expanded`
  - `validated`
  - `blocked`
- `TaxOutputRecord.status`:
  - `ready`
  - `partial`
  - `blocked`

## `EvidenceSet`

Purpose:

- deterministic, capture-scoped evidence output before claim commitment

Product metadata:

- `evidence_set_id`
- `schema_version`
- `selection_fingerprint`
- `capture_manifest_fingerprint`

Owns:

- selected evidence membership
- superseded and blocked alternatives
- deterministic evidence-selection decisions
- typed provenance and locator identity for selected evidence members
- typed observations that do not yet require economic meaning

Record families:

- `EvidenceMemberRecord`
  - `evidence_set_id`
  - `selection_id`
  - `member_id`
  - `source_slug`
  - `adapter_id`
  - `capture_uid`
  - `kind`
  - `locator`
  - `status`
  - `capture_manifest_fingerprint`
- `EvidenceObservationRecord`
  - `evidence_set_id`
  - `member_id`
  - `observation_id`
  - `kind`
  - `key`
  - `observed_at`
  - `precision`
  - `provenance_refs`
- `SelectionRecord`
  - `evidence_set_id`
  - `selection_id`
  - `key`
  - `fingerprint`
  - `basis`
  - `blocking_gap_refs`

Cardinality:

- one `SelectionRecord` exists per `selection_id`
- one or more `EvidenceMemberRecord` rows may belong to one
  `selection_id`
- zero or more `EvidenceObservationRecord` rows may belong to one `member_id`

Sidecar content may include:

- document metadata
- statement row detail
- inventory detail
- candidate-selection reasoning
- parse diagnostics
- rich provenance detail

Controlled vocabularies:

- `SelectionRecord.basis`:
  - `single_member`
  - `coverage`
  - `freshness`
  - `duplicate`
  - `ambiguous_overlap`
  - `upstream_gap`

### First-Slice Critical-Path Observation Kinds

The `EvidenceObservationRecord` shell above is required for every observation.
For the current first slice, these kind-specific kernel fields are also
required:

| `kind` | Kind-owned kernel fields |
| --- | --- |
| `statement_document` | `statement_kind`, `document_effective_at`, `document_effective_precision`, `statement_as_of`, `statement_as_of_precision` |
| `statement_balance_row` | `account_label`, `location_label`, `balance_kind`, `instrument_symbol`, `quantity`, `observed_at`, `precision`, `notes`, `staked_quantity_text`, `value_amount_text`, `value_currency`, `price_amount_text`, `price_currency` |

Rules:

- the kind-specific fields above are kernel meaning, not sidecar detail
- `statement_document.statement_kind` uses the recognized statement-adapter
  kind for the selected document member
- `statement_document.statement_as_of` lifts the current parsed statement
  as-of time and `statement_as_of_precision` follows the
  repo-wide temporal precision contract for that value
- `statement_document.document_effective_at` lifts the current parsed
  document-effective time when present and `document_effective_precision`
  follows the same temporal contract
- `statement_balance_row.observed_at` and `precision` lift
  the current statement-row as-of value and
  precision directly
- `statement_balance_row` account and location labels, quantity, notes, and
  valuation-text
  fields lift the current statement-row contract directly; `pdf_file` and
  `raw_row_ref` stay in provenance and observation keys rather than
  duplicated business fields
- `statement_balance_row.location_label` preserves the source-provided
  lower-scope label, such as a source sub-location name, without
  freezing the source noun into the canonical target field list
- `statement_document` may leave the shell `observed_at` and
  `precision` empty when the meaningful document times are
  instead expressed through the kind-owned document-effective or
  statement-as-of fields
- do not add a generic `observation_payload` blob to stand in for a kind
  table
- no new observation kind may be implemented until this page or the owning
  slice page defines its kernel field table explicitly

Stable ids:

- `evidence_set_id` identifies one capture-scoped evidence emission
- `selection_id` identifies one deterministic evidence-selection
  decision boundary under one evidence set
- `member_id` identifies one selected, superseded, or blocked evidence member
- `observation_id` identifies one typed observation under one evidence member
- `evidence_set_id` uses component array
  `[source_slug, adapter_id, capture_uid, selection_fingerprint]`
- `source_slug` uses the shared source slug for the capture boundary that owns
  the emitted evidence set
- `selection_id` uses component array
  `[evidence_set_id, key]`
- `member_id` uses component array
  `[evidence_set_id, kind, locator]`
- `observation_id` uses component array
  `[member_id, kind, key]`
- `key` is emitted by the evidence-selection stage and
  remains a stable upstream id rather than a downstream recomputation
- because `selection_fingerprint` is part of `evidence_set_id`, a change in
  the authoritative selection state intentionally produces a new
  capture-scoped `EvidenceSet` identity

Ordering:

- `EvidenceMemberRecord` rows sort by tuple
  `[selection_id, status, member_id]`
- `EvidenceObservationRecord` rows sort by `[member_id, observation_id]`
- `SelectionRecord` rows sort by `[selection_id]`

Serialization:

- serialize each evidence record family as its own ordered array
- persist product metadata once per emitted kernel
- use stable object-key ordering
- preserve the declared order above
- sort `provenance_refs` and `blocking_gap_refs` lexicographically

Fingerprint inputs:

- product metadata
- canonical `EvidenceMemberRecord` rows
- canonical `EvidenceObservationRecord` rows
- canonical `SelectionRecord` rows

Must guarantee:

- one capture-scoped authoritative evidence kernel
- deterministic evidence membership and selection decisions
- typed observations that survive beyond intake-time heuristics
- no duplication of member membership inside decision records

Must not:

- force economic meaning
- collapse many selections into one fake product-wide decision
- use file order as identity

Handoff to `ClaimSet`:

- `EvidenceSet` provides selected evidence, typed observations, provenance, and
  deterministic selection decisions
- it does not provide final economic meaning, checkpoint acceptance,
  journal logic, or tax treatment

## `ClaimSet`

Purpose:

- evidence-local meaning before economic truth is fixed

Product metadata:

- `claim_set_id`
- `schema_version`
- `evidence_set_ref`
- `emitter_id`

Owns:

- evidence-local assertions derived from evidence
- explicit scopes and mutually exclusive bundles
- bundle decisions over scopes

Record families:

- `ClaimRecord`
  - `claim_set_id`
  - `claim_scope_id`
  - `bundle_id`
  - `claim_id`
  - `kind`
  - `status`
  - `key`
  - `member_refs`
  - `observation_refs`
  - `effective_at`
  - `precision`
  - `provenance_refs`
- `ClaimBundleRecord`
  - `claim_set_id`
  - `claim_scope_id`
  - `bundle_id`
  - `key`
  - `scope_key`
  - `claim_refs`
- `BundleDecisionRecord`
  - `claim_set_id`
  - `claim_scope_id`
  - `decision_id`
  - `outcome`
  - `accepted_bundle_ref`
  - `rejected_bundle_refs`
  - `deferred_bundle_refs`
  - `basis`
  - `blocking_gap_refs`

Cardinality:

- one or more `ClaimBundleRecord` rows may exist per `claim_scope_id`
- one `BundleDecisionRecord` exists per `claim_scope_id`
- one or more `ClaimRecord` rows may exist per `bundle_id`

Canonical `ClaimRecord.kind` values:

- `activity`
- `balance`
- `instrument_identity`
- `location`
- `legal_owner`
- `beneficial_owner`
- `counterparty`
- `statement`
- `contract_term`
- `valuation`

Controlled vocabularies:

- `BundleDecisionRecord.basis`:
  - `single_bundle`
  - `insufficient_identity`
  - `insufficient_temporal_precision`
  - `conflicting_claims`
  - `upstream_gap`
  - `policy_deferred`
  - `superseded_by_later_claims`

### First-Slice Critical-Path Claim Kinds

The `ClaimRecord` shell above is required for every claim. For the first
bounded slice, these kind-specific kernel fields are also required:

| `kind` | Kind-owned kernel fields |
| --- | --- |
| `activity` | `activity_label`, `location_claim_ref`, `leg_specs` |
| `balance` | `location_claim_ref`, `instrument_claim_refs`, `balance_kind`, `quantity`, `observed_at`, `precision` |
| `instrument_identity` | `scheme`, `value`, `venue`, `instrument_kind`, `name`, `precision` |
| `location` | `location_ref`, `account_label`, `location_label` |
| `beneficial_owner` | `beneficial_owner_ref` |
| `valuation` | `measure_kind`, `purpose`, `amount`, `currency`, `valued_at`, `precision`, `location_claim_ref`, `instrument_claim_refs` |

`leg_specs` entry shape:

- `slot`
- `leg_kind`
- `quantity`
- `instrument_claim_refs`
- `location_claim_ref`
- `subtype`
- `attributed_to_slot`

Current first slice linkage rules:

- `activity` claims own the current evidence-local `activity_label` used by
  the current first slice
- `leg_specs` lift ordered leg meaning from the current
  `EconomicLegDraft` contract, including sign, instrument identity claims,
  optional subtype, optional attributed-leg linkage, and optional location
- retail claims with `kind = activity` use `member_refs` plus the scope used in the current
  first slice
  key `[retail_member_id, raw_row_ref]`; they do not require a retail-row
  observation kind in this pass
- statement-derived claims use both `member_refs` and
  `observation_refs`
- `balance` claims must include the row observation id in
  `observation_refs` and may also include the paired
  `statement_document` observation id for the same statement document
- `valuation` claims are defined now but emit zero rows by default in
  the current first slice until a later owner-doc pass locks numeric
  statement valuation inputs
- `location` claims use `location_label` under the same target-contract rule as
  `statement_balance_row.location_label`: preserve the source-provided
  lower-scope label, but keep the canonical target noun aligned to
  `Location`

### Derived Compatibility Sidecars

Derived compatibility sidecars keep legacy draft and fact reproduction fields
out of `ClaimSet` kernels.

Rules:

- these bridge-only fields must live only in derived compatibility sidecars
  keyed by `claim_id` or `bundle_id`:
  `economic_kind`, `projection_hint`, `accounting_intent_hint`,
  `tax_treatment_hint`, `description`, `tx_hash_or_null`,
  `operation_group_id_or_null`, `confidence`, and `status`
- legacy `provider_operation_key` is satisfied by
  `activity_label` on claims with `kind = activity` and must not be duplicated into a
  compatibility sidecar field
- review markers map to shared support records and sidecars rather than
  claim-kernel fields or compatibility sidecars that masquerade as claim
  meaning
- adapter-local extras may survive only as non-kernel or compatibility sidecar
  detail and never as `ClaimSet` kernel meaning
- do not add a generic `claim_payload` blob to stand in for a kind table
- no non-critical claim kind may be implemented until this page or the
  owning slice page defines its kernel field table explicitly

Stable ids:

- `claim_set_id` identifies one evidence-local claim emission over one evidence
  set
- `claim_scope_id` identifies one evidence-local scope that
  may admit one or more mutually exclusive bundles
- `scope_key` is the stage-owned stable discriminator for one evidence-local
  scope within one claim set
- `bundle_id` identifies one mutually exclusive claim bundle
- `claim_id` identifies one evidence-local claim under one bundle
- `decision_id` identifies one bundle decision record for one
  scope
- `claim_set_id` uses component array `[evidence_set_id, emitter_id]`
- `claim_scope_id` uses component array `[claim_set_id, scope_key]`
- `bundle_id` uses component array
  `[claim_scope_id, key]`
- `claim_id` uses component array `[bundle_id, kind, key]`
- `decision_id` uses component array
  `[claim_set_id, claim_scope_id]`

Ordering:

- `ClaimRecord` rows sort by tuple
  `[bundle_id, kind, effective_at, precision, claim_id]`
- `ClaimBundleRecord` rows sort by
  `[claim_scope_id, key, bundle_id]`
- `BundleDecisionRecord` rows sort by
  `[claim_scope_id, decision_id]`

Serialization:

- serialize each claim record family as its own ordered array
- persist product metadata once per emitted kernel
- use stable object-key ordering
- preserve the declared order above
- sort `member_refs`, `observation_refs`, `provenance_refs`, `claim_refs`,
  `rejected_bundle_refs`, `deferred_bundle_refs`, and `blocking_gap_refs`
  lexicographically

Fingerprint inputs:

- product metadata
- canonical `ClaimRecord` rows
- canonical `ClaimBundleRecord` rows
- canonical `BundleDecisionRecord` rows

Must guarantee:

- evidence-local meaning only
- explicit scope and bundle structure
- preserved ambiguity where one safe final meaning is unavailable
- claim-stage gaps and reviews may attach to `claim_scope_id` when
  no narrower truthful subject has resolved yet
- kind-owned kernel fields are frozen wherever this page defines them; later
  writing and implementation must not invent alternate shells or generic blob
  fields for those kinds
- no promotion of reviews, blockers, or renderer detail into claim
  kinds
- claim-owned bundle decisions that record bundle acceptance, blocking,
  deferral, or supersession without carrying economic truth

Must not:

- force unresolved meaning into final economic meaning or policy outcomes
- treat bridge compatibility annotations as claim kernels
- silently discard materially relevant alternative bundles

Handoff to `EconomicFacts`:

- `ClaimSet` hands off evidence-local assertions, mutually exclusive bundles, and
  bundle decisions
- the economic stage decides which bundle can become accepted economic truth
  and which scopes remain blocked, deferred, or superseded

## `EconomicFacts`

Purpose:

- economic truth the system can safely assert

Product metadata:

- `economic_facts_id`
- `schema_version`
- `claim_set_refs`

Owns:

- accepted economic meaning
- accepted identity resolution needed for economic truth
- stable economic event, leg, and valuation structure
- explicit remaining ambiguity that is still economically safe to preserve

Record families:

- `EconomicEventRecord`
  - `event_id`
  - `bundle_id`
  - `decision_id`
  - `kind`
  - `effective_at`
  - `recorded_at`
  - `settlement_status`
  - `lifecycle_event`
  - `legal_owner_ref`
  - `beneficial_owner_ref`
  - `counterparty_ref`
  - `supersedes_event_id`
- `EconomicLegRecord`
  - `leg_id`
  - `event_id`
  - `role`
  - `subject_ref`
  - `instrument_ref`
  - `location_ref`
  - `quantity`
  - `valuation_ref`
- `ValuationRecord`
  - `valuation_id`
  - `origin_ref`
  - `purpose`
  - `amount`
  - `currency`
  - `valued_at`
  - `precision`
  - `provenance_refs`
  - `confidence`

Controlled vocabularies:

- `EconomicEventRecord.kind`:
  - `asset_movement`
  - `cash_movement`
  - `obligation_or_right`
  - `settlement`
  - `collateral_change`
  - `financing_flow`
  - `fee_or_rebate`
  - `withholding`
  - `lifecycle_restructure`
  - `correction`
- `EconomicLegRecord.role`:
  - `holding_change`
  - `cash_change`
  - `obligation_change`
  - `settlement_change`
  - `collateral_change`
  - `financing_change`
  - `fee`
  - `rebate`
  - `withholding`

Stable ids:

- `economic_facts_id` identifies one accepted economic kernel over one or more
  `ClaimSet` partitions
- `event_id` identifies one accepted economic event
- `leg_id` identifies one stable leg under one accepted event
- `valuation_id` identifies one valuation record used by one or more accepted
  events or legs
- `economic_facts_id` uses component array `[claim_set_refs]`
- `origin_ref` uses `OriginRef` from
  [Target Ids And Refs](../reference/target-ids-and-refs.md)
- `event_id` uses component array `[bundle_id, event_slot]`
- `leg_id` uses component array `[event_id, role, subject_ref, leg_slot]`
- `valuation_id` uses component array
  `[origin_ref, purpose, amount, currency, valued_at, precision]`
- `event_slot` and `leg_slot` are zero-based canonical positions in declared
  event and leg order
- `decision_id` may be referenced for audit, but it does not define
  event identity

Ordering:

- `EconomicEventRecord` rows sort by `effective_at`, then `recorded_at`,
  then `event_id`
- `EconomicLegRecord` rows sort by `[event_id, leg_id]`
- `ValuationRecord` rows sort by `[purpose, valued_at, valuation_id]`

Serialization:

- serialize each economic record family as its own ordered array
- persist product metadata once per emitted kernel
- use stable object-key ordering
- preserve the declared order above
- sort `provenance_refs` lexicographically

Fingerprint inputs:

- product metadata
- canonical `EconomicEventRecord` rows
- canonical `EconomicLegRecord` rows
- canonical `ValuationRecord` rows

Must guarantee:

- accepted event kinds stay jurisdiction-neutral and output-neutral
- event identity is driven by the selected claim bundle, not by compilation
  bookkeeping noise
- event, leg, and valuation records carry the computation-critical
  fields needed for later reconciliation, checkpointing, accounting, and
  tax
- corrections preserve supersession lineage instead of mutating accepted
  economic truth in place

Must not:

- collapse to spot-trade assumptions
- let output hints drive shared runtime behavior
- push leg quantity, location, instrument, or valuation truth into sidecars
  only

Handoff to `ReconciliationState`:

- `EconomicFacts` provides accepted economic events, legs, identity seams,
  settlement state, lifecycle state, and valuations where they are already
  safe
- it records the upstream `claim_set_refs` that justified the accepted
  economic kernel
- it does not claim that continuity is complete, transfers are fully linked, or
  checkpoint truth is accepted

## `ReconciliationState`

Purpose:

- completeness, linkage, continuity, checkpoint proposals, and
  reconciliation-owned blockers

Product metadata:

- `reconciliation_state_id`
- `schema_version`
- `economic_facts_ref`

Owns:

- transfer and settlement linkage
- continuity decisions
- balance targets and assertion outcomes
- reconciliation-owned gaps and readiness
- checkpoint proposals derived from reconciled economics plus checkpoint
  evidence

Record families:

- `ContinuitySegmentRecord`
  - `continuity_segment_id`
  - `subject_ref`
  - `segment_start_at`
  - `segment_end_at`
  - `status`
  - `as_of`
- `EventLinkRecord`
  - `event_link_id`
  - `continuity_segment_id`
  - `kind`
  - `left_event_ref`
  - `right_event_ref`
  - `status`
- `BalanceTargetRecord`
  - `balance_target_id`
  - `continuity_segment_id`
  - `subject_ref`
  - `kind`
  - `as_of`
  - `expected_value`
  - `observed_value`
  - `status`
- `CheckpointProposalRecord`
  - `checkpoint_proposal_id`
  - `continuity_segment_id`
  - `subject_ref`
  - `as_of`
  - `status`
  - `target_refs`
  - `evidence_refs`

Controlled vocabularies:

- `EventLinkRecord.kind`:
  - `transfer`
  - `settlement`
- `EventLinkRecord.status`:
  - `linked`
  - `candidate`
  - `blocked`
  - `superseded`
- `BalanceTargetRecord.kind`:
  - `exact_balance`
  - `range_balance`
  - `boundary_balance`
- `BalanceTargetRecord.status`:
  - `matched`
  - `mismatched`
  - `missing_observation`
  - `blocked`
- `CheckpointProposalRecord.status`:
  - `ready`
  - `partial`
  - `blocked`
  - `superseded`

Sidecar content may include:

- corroboration sidecars
- continuity explanation
- missing-leg detail
- comparison traces
- stage-owned gap and readiness sidecars

Product-root cardinality:

- one `ReconciliationState` kernel owns exactly one `ContinuitySegmentRecord`
- zero or more `EventLinkRecord`, `BalanceTargetRecord`, and
  `CheckpointProposalRecord` rows may exist under that one continuity segment

Stable ids:

- `reconciliation_state_id` identifies one continuity-segment-scoped
  reconciliation kernel
- `continuity_segment_id` identifies one bounded continuity window
- `event_link_id` identifies one owned transfer or settlement linkage
- `balance_target_id` identifies one reconciliation-owned balance assertion
  target
- `checkpoint_proposal_id` identifies one reconciliation-owned checkpoint
  proposal
- `reconciliation_state_id` uses component array
  `[economic_facts_ref, continuity_segment_id]`
- `continuity_segment_id` uses component array
  `[subject_ref, segment_start_at, segment_end_at]`
- `event_link_id` uses component array
  `[continuity_segment_id, kind, left_event_ref, right_event_ref]`
- `balance_target_id` uses component array
  `[continuity_segment_id, subject_ref, kind, as_of, expected_value_fingerprint]`
- `checkpoint_proposal_id` uses component array
  `[continuity_segment_id, subject_ref, as_of, target_refs]`
- `expected_value_fingerprint` is the canonical fingerprint of the
  `AssertionValue` carried in `expected_value`
- `evidence_refs` provide audit support, but they are not part of proposal
  identity

Ordering:

- `ContinuitySegmentRecord` rows sort by
  `[as_of, subject_ref, continuity_segment_id]`
- `EventLinkRecord` rows sort by
  `[continuity_segment_id, kind, left_event_ref, right_event_ref, event_link_id]`
- `BalanceTargetRecord` rows sort by
  `[continuity_segment_id, subject_ref, as_of, balance_target_id]`
- `CheckpointProposalRecord` rows sort by
  `[as_of, subject_ref, continuity_segment_id, checkpoint_proposal_id]`

Serialization:

- serialize each reconciliation record family as its own ordered array
- persist product metadata once per emitted kernel
- use stable object-key ordering
- preserve the declared order above
- sort `target_refs` and `evidence_refs` lexicographically

Fingerprint inputs:

- product metadata
- canonical `ContinuitySegmentRecord` rows
- canonical `EventLinkRecord` rows
- canonical `BalanceTargetRecord` rows
- canonical `CheckpointProposalRecord` rows

Must guarantee:

- explicit completeness decisions
- explicit continuity decisions
- explicit missing-leg and missing-evidence surfaces
- reconciliation-stage gaps and reviews may attach to `balance_target_id` when
  one exact target is the truthful blocker or review scope
- preservation of partial truth when the whole window is not yet clean
- no rewriting of upstream economics to satisfy checks

Must not:

- reclassify upstream economics to make continuity easier
- bury missing evidence inside kernel-scope readiness summaries
- use value refs that point to undefined sidecar values outside the kernel

Handoff to `Checkpoint`:

- `ReconciliationState` provides checkpoint proposals, corroboration,
  continuity outcomes, and reconciliation-owned blockers
- checkpoint acceptance still belongs to the checkpoint stage

## `Checkpoint`

Purpose:

- accepted checkpoint truth and acceptance basis

Product metadata:

- `checkpoint_id`
- `schema_version`
- `reconciliation_state_refs`
- `as_of`

Owns:

- accepted checkpoint assertions
- adopted opening state when intentionally used
- acceptance basis, trust level, and continuity into accepted state

Record families:

- `CheckpointRecord`
  - `checkpoint_id`
  - `as_of`
  - `assertion_ids`
- `CheckpointAssertionRecord`
  - `checkpoint_assertion_id`
  - `checkpoint_id`
  - `subject_ref`
  - `kind`
  - `as_of`
  - `accepted_value`
  - `trust_level`
  - `basis`
  - `support_kind`
  - `continuity_kind`
- `proposal_refs`

Controlled vocabularies:

- `CheckpointAssertionRecord.kind`:
  - `position_quantity`
  - `cash_quantity`
  - `basis_value`
  - `ownership`
  - `location`
- `trust_level`:
  - `filing_ready`
  - `analysis_ready`
  - `manual_only`
- `CheckpointAssertionRecord.basis`:
  - `document_evidence`
  - `reported_balance`
  - `reconciled_rollforward`
  - `adopted_opening`
  - `manual_assertion`
- `CheckpointAssertionRecord.support_kind`:
  - `document_balance`
  - `reported_balance`
  - `location_balance`
  - `inventory_observation`
  - `manual_assertion`
- `continuity_kind`:
  - `direct_observation`
  - `reconciled_rollforward`
  - `opening_rollforward`
  - `partial_rollforward`

Sidecar content may include:

- supporting evidence refs
- supporting provenance detail
- continuity explanation
- opening-state adoption detail
- acceptance rationale

Product-root cardinality:

- one `Checkpoint` kernel owns exactly one `CheckpointRecord`
- one or more `CheckpointAssertionRecord` rows may exist under that one
  checkpoint record

Stable ids:

- `checkpoint_id` identifies one accepted checkpoint kernel and its accepted
  root record
- `checkpoint_assertion_id` identifies one accepted checkpoint truth record for
  one subject and one as-of point
- `checkpoint_id` uses component array
  `[reconciliation_state_refs, as_of]`
- `checkpoint_assertion_id` uses component array
  `[kind, as_of, subject_ref, accepted_value_fingerprint]`
- `accepted_value_fingerprint` is the canonical fingerprint of one
  `AssertionValue` variant from [Domain Ontology](domain-ontology.md)

Ordering:

- `CheckpointRecord` rows sort by `[as_of, checkpoint_id]`
- `CheckpointAssertionRecord` rows sort by tuple
  `[as_of, subject_ref.subject_kind, subject_ref.subject_id, checkpoint_assertion_id]`

Serialization:

- serialize each checkpoint record family as its own ordered array
- persist product metadata once per emitted kernel
- use stable object-key ordering
- preserve the declared order above
- sort `proposal_refs` lexicographically

Lineage rule:

- `proposal_refs` uses ordered `checkpoint_proposal_id` values
  when reconciliation-owned proposals support the accepted assertion
- product-scope `reconciliation_state_refs` remain the broader upstream
  partition lineage; assertion-level proposal refs point only at the accepted
  proposal lineage when that narrower lineage exists

Fingerprint inputs:

- product metadata
- canonical `CheckpointRecord` rows
- canonical `CheckpointAssertionRecord` rows

Minimum admissibility rules:

- `filing_ready` requires:
  - `basis` other than `manual_assertion`
  - `support_kind` other than `manual_assertion`
  - `continuity_kind` other than `partial_rollforward`
- `analysis_ready` may use `manual_assertion` or `partial_rollforward`, but
  the lower-trust basis stays explicit in the accepted checkpoint record
- `manual_only` is required when accepted checkpoint truth relies solely on
  manual assertion without evidence-backed support
- `adopted_opening` remains a distinct acceptance basis and must preserve
  provenance plus the continuity kind used to roll it into accepted state

Must guarantee:

- accepted checkpoint truth is first-class
- evidence-backed support remains preferred
- manual assertions do not silently become filing-ready checkpoint truth
- adopted opening state remains explicit instead of masquerading as direct
  observation

Must not:

- silently elevate manual convenience inputs into filing-ready truth
- hide the acceptance basis, trust level, or continuity assumptions

Handoff to `Journal` and `TaxInputs`:

- `Checkpoint` provides accepted assertions, accepted opening state where used,
  and the acceptance basis
- downstream accounting and tax stages consume that accepted truth rather than
  re-deciding checkpoint trust locally

## `Journal`

Purpose:

- accounting expansion and validation over accepted truth

Product metadata:

- `journal_id`
- `schema_version`
- `economic_facts_refs`
- `checkpoint_ref`

Owns:

- journal entry and posting expansion
- accounting validation results
- accounting-owned gaps

Record families:

- `JournalEntryRecord`
  - `journal_id`
  - `entry_id`
  - `kind`
  - `effective_at`
  - `event_refs`
  - `assertion_refs`
  - `status`
- `PostingRecord`
  - `posting_id`
  - `entry_id`
  - `account_ref`
  - `commodity_ref`
  - `amount`
  - `side`
  - `origin_ref`
- `EntryCheckRecord`
  - `check_id`
  - `entry_id`
  - `kind`
  - `status`
  - `blocking_gap_refs`

Controlled vocabularies:

- `JournalEntryRecord.kind`:
  - `event`
  - `opening`
  - `adjustment`
- `side`:
  - `debit`
  - `credit`
- `EntryCheckRecord.kind`:
  - `balanced`
  - `commodity_balance`
  - `unsupported_mapping`
- `EntryCheckRecord.status`:
  - `passed`
  - `blocked`

Sidecar content may include:

- posting explanation
- validation notes
- renderer-facing annotations
- accounting-owned gap sidecars

Product-root cardinality:

- one `Journal` kernel may contain many entries, postings, and validations
- one emitted `Journal` kernel must contain exactly one distinct `journal_id`

Stable ids:

- `journal_id` identifies one emitted `Journal` kernel over the declared
  upstream truth set
- `entry_id` identifies one journal entry
- `posting_id` identifies one posting under one journal entry
- `check_id` identifies one journal entry check result
- `account_ref`, `commodity_ref`, and `origin_ref` use `AccountRef`,
  `CommodityRef`, and `OriginRef` from
  [Target Ids And Refs](../reference/target-ids-and-refs.md)
- `journal_id` uses component array
  `[checkpoint_ref, economic_facts_refs]`
- `entry_id` uses component array
  `[journal_id, kind, effective_at, event_refs, assertion_refs]`
- `posting_id` uses component array
  `[entry_id, account_ref, commodity_ref, amount, side, origin_ref]`
- `check_id` uses component array `[entry_id, kind]`

Ordering:

- `JournalEntryRecord` rows sort by `[effective_at, kind, entry_id]`
- `PostingRecord` rows sort by
  `[entry_id, side, account_ref, commodity_ref, origin_ref, posting_id]`
- `EntryCheckRecord` rows sort by `[entry_id, kind, check_id]`

Serialization:

- serialize each journal record family as its own ordered array
- persist product metadata once per emitted kernel
- use stable object-key ordering
- preserve the declared order above
- sort `event_refs`, `assertion_refs`, and
  `blocking_gap_refs` lexicographically

Fingerprint inputs:

- product metadata
- canonical `JournalEntryRecord` rows
- canonical `PostingRecord` rows
- canonical `EntryCheckRecord` rows

Must guarantee:

- deterministic posting expansion
- explicit validation
- explicit unsupported accounting mapping
- posting fields required for validation remain part of the kernel

Must not:

- become a truth repair layer
- hide postings or validation blockers in sidecars only
- claim to operate without accepted `EconomicFacts` and `Checkpoint` inputs

Handoff to downstream renderers:

- `Journal` provides accounting-owned postings, validation results, and
  accounting-owned blockers
- renderer-specific row shapes stay at output boundaries rather than becoming
  part of the shared journal contract

## `TaxInputs`

Purpose:

- policy-ready, jurisdiction-neutral tax input surface

Product metadata:

- `tax_inputs_id`
- `schema_version`
- `economic_facts_refs`
- `checkpoint_ref`

Owns:

- tax inputs derived from reconciled economics plus accepted checkpoint
  truth
- explicit tax-owned blockers where upstream truth is still not tax-complete

Record families:

- `TaxInputRecord`
  - `tax_input_id`
  - `kind`
  - `tax_year`
  - `basis_pool_ref`
  - `beneficial_owner_ref`
  - `instrument_ref`
  - `effective_at`
  - `quantity`
  - `direction`
  - `valuation_ref`
  - `counterparty_ref`
  - `event_refs`
  - `assertion_refs`
  - `basis_transition_ref`
- `BasisTransitionRecord`
  - `basis_transition_id`
  - `basis_pool_ref`
  - `from_tax_input_ref`
  - `to_tax_input_ref`
  - `kind`

Controlled vocabularies:

- `TaxInputRecord.kind`:
  - `acquisition`
  - `disposition`
  - `income`
  - `expense_or_fee`
  - `financing_cost`
  - `internal_transfer`
  - `basis_adjustment`
  - `corporate_action`
- `direction`:
  - `increase`
  - `decrease`
  - `neutral`
- `BasisTransitionRecord.kind`:
  - `pool_open`
  - `pool_adjustment`
  - `pool_close`
  - `carry_forward`

Sidecar content may include:

- tax-relevant valuation detail
- supporting ownership and counterparty detail
- pool-transition explanation
- tax-owned blocker detail

Stable ids:

- `tax_inputs_id` identifies one emitted `TaxInputs` kernel
- `tax_input_id` identifies one tax input record
- `basis_transition_id` identifies one basis or pool transition
- `tax_inputs_id` uses component array
  `[checkpoint_ref, economic_facts_refs]`
- `tax_input_id` uses component array
  `[tax_year, kind, basis_pool_ref, beneficial_owner_ref, instrument_ref, effective_at, quantity, direction, event_refs, assertion_refs]`
- `basis_transition_id` uses component array
  `[basis_pool_ref, kind, from_tax_input_ref, to_tax_input_ref]`

Ordering:

- `TaxInputRecord` rows sort by tuple
  `[tax_year, basis_pool_ref.tax_policy_id, basis_pool_ref.jurisdiction_or_regime, basis_pool_ref.beneficial_owner_ref, basis_pool_ref.pool_key, kind, effective_at, tax_input_id]`
- `BasisTransitionRecord` rows sort by
  `[basis_pool_ref.tax_policy_id, basis_pool_ref.jurisdiction_or_regime, basis_pool_ref.beneficial_owner_ref, basis_pool_ref.pool_key, kind, basis_transition_id]`

Serialization:

- serialize each tax input record family as its own ordered array
- persist product metadata once per emitted kernel
- use stable object-key ordering
- preserve the declared order above
- sort `event_refs` and `assertion_refs` lexicographically

Fingerprint inputs:

- product metadata
- canonical `TaxInputRecord` rows
- canonical `BasisTransitionRecord` rows

Must guarantee:

- jurisdiction-neutral tax inputs
- explicit basis-affecting state changes
- explicit tax-owned blockers where upstream truth is not tax-complete
- tax-incomplete items stay explicit instead of being upgraded into guessed
  treatment

Must not:

- embed one jurisdiction's output schema
- decide source meaning, reconciliation truth, checkpoint truth, or accounting
  truth
- push effective time, quantity, direction, or basis transitions into
  sidecars only

Handoff to `TaxOutputs`:

- `TaxInputs` provides the tax input surface that selected policies operate
  on
- the policy layer decides treatment and output shape, not the upstream claim,
  economic, reconciliation, or checkpoint layers

## `TaxOutputs`

Purpose:

- one selected tax policy's outputs

Product metadata:

- `tax_outputs_id`
- `schema_version`
- `tax_inputs_ref`
- `tax_policy_id`
- `tax_year`

Owns:

- policy-specific summaries, forms, schedules, and carry-forward state
- tax-policy explanations, limitations, and unsupported outputs
- tax-owned blockers that survive policy execution

Record families:

- `TaxOutputRecord`
  - `tax_output_id`
  - `tax_policy_id`
  - `kind`
  - `tax_year`
  - `status`
  - `basis_pool_refs`
- `CarryForwardRecord`
  - `carry_forward_id`
  - `tax_output_id`
  - `basis_pool_ref`
  - `next_tax_year`
  - `fingerprint`
- `UnsupportedTaxInputRecord`
  - `unsupported_tax_input_id`
  - `tax_output_id`
  - `tax_input_ref`
  - `blocking_gap_refs`

Controlled vocabularies:

- `TaxOutputRecord.kind`:
  - `realized_gain`
  - `income`
  - `expense`
  - `carry_forward`
  - `unsupported_input`

Sidecar content may include:

- policy-specific summaries
- schedules and forms
- carry-forward explanation
- unsupported tax input notes

Product-root cardinality:

- one `TaxOutputs` kernel may contain many `TaxOutputRecord`,
  `CarryForwardRecord`, and `UnsupportedTaxInputRecord` rows
- one emitted `TaxOutputs` kernel must contain exactly one `tax_policy_id` and one
  `tax_year`

Stable ids:

- `tax_outputs_id` identifies one emitted `TaxOutputs` kernel
- `tax_output_id` identifies one policy-owned output emission
- `carry_forward_id` identifies one carry-forward state record
- `unsupported_tax_input_id` identifies one persisted unsupported tax input
  record
- `tax_outputs_id` uses component array `[tax_inputs_ref, tax_policy_id, tax_year]`
- `tax_output_id` uses component array
  `[tax_policy_id, kind, tax_year, basis_pool_refs]`
- `carry_forward_id` uses component array
  `[tax_output_id, basis_pool_ref, next_tax_year]`
- `unsupported_tax_input_id` uses component array
  `[tax_output_id, tax_input_ref]`

Ordering:

- `TaxOutputRecord` rows sort by
  `[tax_policy_id, tax_year, kind, tax_output_id]`
- `CarryForwardRecord` rows sort by
  `[tax_output_id, next_tax_year, basis_pool_ref, carry_forward_id]`
- `UnsupportedTaxInputRecord` rows sort by
  `[tax_output_id, tax_input_ref, unsupported_tax_input_id]`

Serialization:

- serialize each tax-output record family as its own ordered array
- persist product metadata once per emitted kernel
- use stable object-key ordering
- preserve the declared order above
- sort `basis_pool_refs` and `blocking_gap_refs` lexicographically

Fingerprint inputs:

- product metadata
- canonical `TaxOutputRecord` rows
- canonical `CarryForwardRecord` rows
- canonical `UnsupportedTaxInputRecord` rows

Must guarantee:

- outputs are derived from `TaxInputs` through selected tax policies
- policy selection is explicit
- unsupported tax inputs stay explicit instead of being silently omitted

Must not:

- claim to come directly from `EconomicFacts` or `ReconciliationState`
- backfill earlier-stage meaning gaps by guessing
- claim to operate without accepted `EconomicFacts` and `Checkpoint` inputs

## Shared Contract References

The pipeline products rely on shared supporting contracts defined elsewhere:

- [Current Bridge Contracts](current-bridge-contracts.md) for the live bridge
  runtime truth
- [Bridge To Target Mapping](bridge-to-target-mapping.md) for the primary
  current-to-target transformation rules and migration authority matrix
- [First Slice Contract](../reference/first-slice-contract.md) for the current
  first replay and parity contract
- [First Downstream Slice Contract](../reference/first-downstream-slice-contract.md)
  for the current first `EconomicFacts -> ReconciliationState -> Checkpoint`
  contract
- [Domain Ontology](domain-ontology.md) for entity seams, refs,
  `AssertionValue`, and package ownership
- [Gaps And Readiness](gaps-and-readiness.md) for `GapRecord`,
  `GapExplanation`, reviews, readiness, and `SubjectRef`
- [Reconciliation And Tax Architecture](reconciliation-tax-architecture.md) for
  persistence rules, partitioning rules, and fast-path expectations
