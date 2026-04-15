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
  or evidence is the normal recovery path for incompatible artifacts

### Stable Id Format

- every stable id defined on this page uses the format
  `<kind>:<sha256(lowercase-hex)>`
- the hash input is one canonical UTF-8 JSON array of ordered components
- component arrays use the owning product's canonical scalar forms exactly as
  emitted; do not add hidden trimming, lowercasing, or resorting outside the
  declared tuple rules

### Product Id And Upstream Ref Rules

- every target product carries one product id in product metadata
- `EvidenceSet` and `ClaimSet` keep `evidence_set_id` and `claim_set_id` as
  their product ids
- later products use dedicated product ids:
  `economic_facts_id`, `reconciliation_state_id`, `checkpoint_run_id`,
  `journal_run_id`, `tax_inputs_id`, and `tax_outputs_id`
- upstream product metadata refs use product ids only; they never use
  `dataset_id` or a raw kernel fingerprint
- ordered metadata fields such as `claim_set_refs`,
  `reconciliation_state_refs`, and `economic_facts_refs` sort
  lexicographically by product id unless the owning product declares a
  stronger canonical order
- `dataset_id` remains a derived shared-support and reporting attachment only;
  it is not a product id or upstream product ref

### Record Reference Rule

- when a kernel field name ends with `_ref`, `_refs`, or `_id_or_null` and the
  stem names one target product owned on this page, the field uses that
  product's metadata id or ordered product-id list
- when a kernel field name ends with `_ref`, `_refs`, or `_id_or_null` and the
  stem names one target record family owned on this page, the field uses that
  record family's stable id or ordered stable-id list
- helper tuple refs such as `SubjectRef`, `BasisPoolRef`,
  `ValuationSourceRef`, `AccountRef`, `CommodityRef`, and `OriginRef` remain
  owned by their helper pages and are called out explicitly where used

### Composite Tuple Rules

- `SubjectRef` serializes and sorts as `[subject_kind, subject_id]`
- `BasisPoolRef` serializes and sorts as
  `[tax_policy_id, jurisdiction_or_regime, beneficial_owner_ref, pool_scope]`
- when one stable-id recipe, ordering rule, or fingerprint input includes a
  domain ref whose canonical tuple is owned by
  [Domain Ontology](domain-ontology.md), use that tuple form rather than an
  object-name shorthand

### Temporal Scalar Rule

- where a field or id recipe uses a temporal scalar such as `effective_at`,
  `target_as_of_at`, `asserted_as_of_at`, or `valued_at_or_null`, the
  canonical serialized form must preserve whether the meaning is date-scoped
  or timestamp-scoped
- stages may carry an additional precision field when that stage needs it
  operationally, but the stable id and fingerprint use the canonical temporal
  scalar only once

### Kernel And Sidecar Rule

- every target product separates a compact computational kernel from optional
  sidecars
- the kernel holds stable ids, ordering keys, owning decisions, and the
  downstream-required references needed for replay and reducers
- sidecars hold provenance detail, explanation, reviews, comparison traces,
  policy notes, and other non-kernel context
- sidecars must not become the only copy of determinant state or business
  meaning
- any later rehydration path must join through stable ids emitted by the
  kernel

### Dataset Id And Sidecar Attachment

- every target product has one canonical kernel fingerprint
- the shared `dataset_id` contract is owned by
  [Gaps And Readiness](gaps-and-readiness.md)
- `dataset_id` is derived from the emitted kernel fingerprint after canonical
  fingerprinting; it is not part of kernel metadata or fingerprint inputs
- `dataset_id` is the product-level attachment surface for readiness,
  comparison, and other shared sidecars when no narrower truthful scope exists
- `dataset_id` is not a substitute for a narrower record id or stage-owned
  scope such as `selection_group_id`, `continuity_segment_id`, or
  `checkpoint_candidate_id`

### Shared Kernel Status Vocabulary

Use these bounded status vocabularies across target kernels:

- `selection_status`:
  - `selected`
  - `superseded`
  - `blocked`
- `claim_status`:
  - `asserted`
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

- deterministic, capture-scoped evidence output before semantic commitment

Product metadata:

- `evidence_set_id`
- `schema_version`
- `selection_plan_fingerprint`
- `manifest_fingerprint_ref`

Owns:

- selected evidence membership
- superseded and blocked alternatives
- deterministic evidence-selection decisions
- typed provenance and locator identity for selected evidence members
- source-local typed observations that do not yet require economic meaning

Record families:

- `EvidenceMemberRecord`
  - `evidence_set_id`
  - `selection_group_id`
  - `member_id`
  - `source`
  - `adapter_id`
  - `capture_uid`
  - `member_family`
  - `member_locator_identity`
  - `selection_status`
  - `manifest_fingerprint_ref`
- `EvidenceObservationRecord`
  - `evidence_set_id`
  - `member_id`
  - `observation_id`
  - `observation_family`
  - `observation_anchor`
  - `observed_at_or_null`
  - `observed_precision_or_null`
  - `provenance_refs`
- `SelectionDecisionRecord`
  - `evidence_set_id`
  - `selection_group_id`
  - `selection_group_anchor`
  - `selection_plan_fingerprint`
  - `decision_basis`
  - `blocking_gap_refs`

Cardinality:

- one `SelectionDecisionRecord` exists per `selection_group_id`
- one or more `EvidenceMemberRecord` rows may belong to one
  `selection_group_id`
- zero or more `EvidenceObservationRecord` rows may belong to one `member_id`

Envelope or sidecar content may include:

- document metadata
- statement row detail
- inventory detail
- candidate-selection reasoning
- parse diagnostics
- rich provenance payloads

Controlled vocabularies:

- `decision_basis`:
  - `single_member_match`
  - `coverage_preferred`
  - `freshness_preferred`
  - `content_duplicate`
  - `ambiguous_overlap`
  - `upstream_blocker`

### First-Slice Critical-Path Observation Families

The `EvidenceObservationRecord` shell above is required for every observation.
For the first bounded slice, these family-specific kernel fields are also
required:

| `observation_family` | Family-owned kernel fields |
| --- | --- |
| `document_identity` | `statement_kind`, `document_effective_at_or_null`, `document_effective_precision_or_null`, `statement_as_of_at_or_null`, `statement_as_of_precision_or_null` |
| `coinbase_statement_balance_row` | `account_label_or_null`, `wallet_label_or_null`, `balance_kind`, `asset_symbol`, `quantity_or_null`, `observed_at_or_null`, `observed_precision_or_null`, `notes_or_null`, `staked_quantity_text_or_null`, `value_amount_text_or_null`, `value_currency_or_null`, `price_amount_text_or_null`, `price_currency_or_null` |

Rules:

- the family-specific fields above are kernel meaning, not sidecar detail
- `document_identity.statement_kind` uses the recognized statement-adapter
  kind for the selected document member
- `document_identity.statement_as_of_at_or_null` lifts the current parsed
  statement as-of time and `statement_as_of_precision_or_null` follows the
  repo-wide temporal precision contract for that value
- `document_identity.document_effective_at_or_null` lifts the current parsed
  document-effective time when present and
  `document_effective_precision_or_null` follows the same temporal contract
- `coinbase_statement_balance_row.observed_at_or_null` and
  `observed_precision_or_null` lift the current statement-row as-of value and
  precision directly
- `coinbase_statement_balance_row` label, quantity, note, and valuation-text
  fields lift the current statement-row contract directly; `pdf_file` and
  `raw_row_ref` stay in provenance and observation anchors rather than
  duplicated business payload
- `document_identity` may leave the shell `observed_at_or_null` and
  `observed_precision_or_null` empty when the meaningful document times are
  instead expressed through the family-owned document-effective or
  statement-as-of fields
- do not add a generic `observation_payload` blob to stand in for a family
  table
- no new observation family may be implemented until this page or the owning
  bounded slice page defines its kernel field table explicitly

Stable ids:

- `evidence_set_id` identifies one capture-scoped evidence emission
- `selection_group_id` identifies one deterministic evidence-selection
  decision boundary under one evidence set
- `member_id` identifies one selected, superseded, or blocked evidence member
- `observation_id` identifies one typed observation under one evidence member
- `evidence_set_id` uses component array
  `[source, adapter_id, capture_uid, selection_plan_fingerprint]`
- `selection_group_id` uses component array
  `[evidence_set_id, selection_group_anchor]`
- `member_id` uses component array
  `[evidence_set_id, member_family, member_locator_identity]`
- `observation_id` uses component array
  `[member_id, observation_family, observation_anchor]`
- `selection_group_anchor` is emitted by the evidence-selection stage and
  remains a stable upstream id rather than a downstream recomputation
- because `selection_plan_fingerprint` is part of `evidence_set_id`, a change
  in the authoritative selection plan intentionally produces a new
  capture-scoped `EvidenceSet` identity

Ordering:

- `EvidenceMemberRecord` rows sort by tuple
  `[selection_group_id, selection_status, member_id]`
- `EvidenceObservationRecord` rows sort by `[member_id, observation_id]`
- `SelectionDecisionRecord` rows sort by `[selection_group_id]`

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
- canonical `SelectionDecisionRecord` rows

Must guarantee:

- one capture-scoped authoritative evidence kernel
- deterministic evidence membership and selection decisions
- typed observations that survive beyond intake-time heuristics
- no duplication of member membership inside decision records

Must not:

- force economic interpretation
- collapse many selection groups into one fake product-wide decision
- use file order as identity

Handoff to `ClaimSet`:

- `EvidenceSet` provides selected evidence, typed observations, provenance, and
  deterministic selection decisions
- it does not provide final economic interpretation, checkpoint acceptance,
  journal logic, or tax treatment

## `ClaimSet`

Purpose:

- semantic-only source-local meaning before economic truth is fixed

Product metadata:

- `claim_set_id`
- `schema_version`
- `evidence_set_ref`
- `claim_emitter_id`

Owns:

- source-local semantic assertions derived from evidence
- explicit interpretation scope and mutually exclusive semantic bundles
- compilation decisions over interpretation scopes

Record families:

- `ClaimRecord`
  - `claim_set_id`
  - `interpretation_scope_id`
  - `bundle_id`
  - `claim_id`
  - `claim_family`
  - `claim_status`
  - `claim_anchor`
  - `evidence_member_refs`
  - `evidence_observation_refs`
  - `effective_at_or_null`
  - `effective_precision_or_null`
  - `provenance_refs`
- `InterpretationBundleRecord`
  - `claim_set_id`
  - `interpretation_scope_id`
  - `bundle_id`
  - `bundle_discriminator`
  - `scope_anchor`
  - `claim_refs`
- `CompilationDecisionRecord`
  - `claim_set_id`
  - `interpretation_scope_id`
  - `compilation_decision_id`
  - `compilation_outcome`
  - `selected_bundle_id_or_null`
  - `rejected_bundle_refs`
  - `deferred_bundle_refs`
  - `resolution_basis`
  - `blocking_gap_refs`

Cardinality:

- one or more `InterpretationBundleRecord` rows may exist per
  `interpretation_scope_id`
- one `CompilationDecisionRecord` exists per `interpretation_scope_id`
- one or more `ClaimRecord` rows may exist per `bundle_id`

Canonical claim families:

- `ActivityClaim`
- `BalanceObservationClaim`
- `InstrumentIdentityClaim`
- `LocationClaim`
- `LegalOwnerClaim`
- `BeneficialOwnerClaim`
- `CounterpartyClaim`
- `StatementClaim`
- `ContractTermClaim`
- `ValuationClaim`

Controlled vocabularies:

- `resolution_basis`:
  - `single_bundle_match`
  - `insufficient_identity`
  - `insufficient_temporal_precision`
  - `conflicting_claims`
  - `upstream_blocker`
  - `policy_deferred`
  - `superseded_by_later_claims`

### First-Slice Critical-Path Claim Families

The `ClaimRecord` shell above is required for every claim. For the first
bounded slice, these family-specific kernel fields are also required:

| `claim_family` | Family-owned kernel fields |
| --- | --- |
| `ActivityClaim` | `provider_activity_kind`, `location_claim_ref_or_null`, `activity_leg_specs` |
| `BalanceObservationClaim` | `location_claim_ref`, `instrument_claim_refs`, `balance_kind`, `quantity`, `observed_at_or_null`, `observed_precision_or_null` |
| `InstrumentIdentityClaim` | `scheme`, `value`, `venue_or_null`, `kind_hint`, `display_name_or_null`, `precision_hint_or_null` |
| `LocationClaim` | `location_ref`, `account_label_or_null`, `wallet_label_or_null` |
| `BeneficialOwnerClaim` | `beneficial_owner_ref` |
| `ValuationClaim` | `valuation_measure_kind`, `valuation_purpose`, `amount`, `currency`, `valued_at_or_null`, `valued_precision_or_null`, `location_claim_ref_or_null`, `instrument_claim_refs` |

`activity_leg_specs` entry shape:

- `leg_slot`
- `leg_kind`
- `quantity`
- `instrument_claim_refs`
- `location_claim_ref_or_null`
- `subtype_or_null`
- `attributed_to_leg_slot_or_null`

First-slice linkage rules:

- `ActivityClaim.provider_activity_kind` is the canonical home for the current
  provider-local activity type used by the bounded slice
- `activity_leg_specs` lift ordered leg meaning from the current
  `EconomicLegDraft` contract, including sign, instrument identity claims,
  optional subtype, optional attributed-leg linkage, and optional location
- retail activity claims use `evidence_member_refs` plus the first-slice scope
  anchor `[retail_member_id, raw_row_ref]`; they do not require a retail-row
  observation family in this pass
- statement-derived claims use both `evidence_member_refs` and
  `evidence_observation_refs`
- `BalanceObservationClaim` must include the row observation id in
  `evidence_observation_refs` and may also include the paired
  `document_identity` observation id for the same statement document
- `ValuationClaim` is canonically defined now but emits zero rows by default in
  the first bounded slice until a later owner-doc pass locks canonical numeric
  statement valuation inputs

### Derived Compatibility Sidecars

Derived compatibility sidecars keep legacy draft and fact reproduction fields out of
canonical `ClaimSet` payloads.

Rules:

- these bridge-only fields must live only in derived compatibility sidecars
  keyed by `claim_id` or `bundle_id`:
  `economic_kind`, `projection_hint`, `accounting_intent_hint`,
  `tax_treatment_hint`, `description`, `tx_hash_or_null`,
  `operation_group_id_or_null`, `confidence`, and `status`
- `provider_operation_key` is satisfied by
  `ActivityClaim.provider_activity_kind` and must not be duplicated into a
  compatibility sidecar field
- review markers map to shared support artifacts rather than canonical claims
  or bridge-compat semantic payloads
- adapter-local extras may survive only as envelope or compatibility-sidecar
  detail and never as canonical `ClaimSet` kernel meaning
- do not add a generic `claim_payload` blob to stand in for a family table
- no non-critical claim family may be implemented until this page or the
  owning bounded slice page defines its kernel field table explicitly

Stable ids:

- `claim_set_id` identifies one semantic emission over one evidence set
- `interpretation_scope_id` identifies one provider-local semantic scope that
  may admit one or more mutually exclusive bundles
- `bundle_id` identifies one mutually exclusive semantic bundle
- `claim_id` identifies one semantic assertion under one bundle
- `compilation_decision_id` identifies one compilation-decision record for one
  interpretation scope
- `claim_set_id` uses component array `[evidence_set_id, claim_emitter_id]`
- `interpretation_scope_id` uses component array `[claim_set_id, scope_anchor]`
- `bundle_id` uses component array
  `[interpretation_scope_id, bundle_discriminator]`
- `claim_id` uses component array `[bundle_id, claim_family, claim_anchor]`
- `compilation_decision_id` uses component array
  `[claim_set_id, interpretation_scope_id]`

Ordering:

- `ClaimRecord` rows sort by tuple
  `[bundle_id, claim_family, effective_at_or_null, effective_precision_or_null, claim_id]`
- `InterpretationBundleRecord` rows sort by
  `[interpretation_scope_id, bundle_discriminator, bundle_id]`
- `CompilationDecisionRecord` rows sort by
  `[interpretation_scope_id, compilation_decision_id]`

Serialization:

- serialize each claim record family as its own ordered array
- persist product metadata once per emitted kernel
- use stable object-key ordering
- preserve the declared order above
- sort `evidence_member_refs`, `evidence_observation_refs`, `provenance_refs`, `claim_refs`,
  `rejected_bundle_refs`, `deferred_bundle_refs`, and `blocking_gap_refs`
  lexicographically

Fingerprint inputs:

- product metadata
- canonical `ClaimRecord` rows
- canonical `InterpretationBundleRecord` rows
- canonical `CompilationDecisionRecord` rows

Must guarantee:

- source-local semantics only
- explicit interpretation scope and bundle structure
- preserved ambiguity where one safe final interpretation is unavailable
- claim-stage gaps and reviews may attach to `interpretation_scope_id` when
  no narrower truthful subject has resolved yet
- family-owned kernel fields are frozen wherever this page defines them; later
  writing and implementation must not invent alternate shells or generic
  payload blobs for those families
- no semantic promotion of reviews, blockers, or renderer metadata into claim
  families
- claim-owned compilation decisions that record bundle acceptance, blocking,
  deferral, or supersession without carrying economic payloads

Must not:

- force unresolved meaning into final economic or policy interpretations
- treat bridge compatibility annotations as canonical claims
- silently discard materially relevant alternative bundles

Handoff to `EconomicFacts`:

- `ClaimSet` hands off source-local assertions, mutually exclusive bundles, and
  compilation decisions
- the compiler decides which bundle can become accepted economic truth and
  which scopes remain blocked, deferred, or superseded

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
  - `compilation_decision_id`
  - `event_family`
  - `effective_at_or_null`
  - `recorded_at`
  - `settlement_state`
  - `lifecycle_state`
  - `legal_owner_ref_or_null`
  - `beneficial_owner_ref_or_null`
  - `counterparty_ref_or_null`
  - `supersedes_event_id_or_null`
- `EconomicLegRecord`
  - `leg_id`
  - `event_id`
  - `leg_role`
  - `subject_ref`
  - `instrument_ref_or_null`
  - `location_ref_or_null`
  - `quantity`
  - `valuation_ref_or_null`
- `ValuationRecord`
  - `valuation_id`
  - `valuation_source_ref`
  - `valuation_purpose`
  - `amount`
  - `currency`
  - `valued_at_or_null`
  - `valued_precision_or_null`
  - `provenance_refs`
  - `confidence`

Controlled vocabularies:

- `event_family`:
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
- `leg_role`:
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
- `economic_facts_id` uses component array `[ordered_claim_set_refs]`
- `valuation_source_ref` uses `ValuationSourceRef` from
  [Target Contract Primitives](../reference/target-contract-primitives.md)
- `event_id` uses component array `[bundle_id, event_index]`
- `leg_id` uses component array `[event_id, leg_role, subject_ref, leg_index]`
- `valuation_id` uses component array
  `[valuation_source_ref, valuation_purpose, amount, currency, valued_at_or_null, valued_precision_or_null]`
- `event_index` and `leg_index` are zero-based canonical positions in declared
  event and leg order
- `compilation_decision_id` may be referenced for audit, but it does not define
  event identity

Ordering:

- `EconomicEventRecord` rows sort by `effective_at_or_null`, then `recorded_at`,
  then `event_id`
- `EconomicLegRecord` rows sort by `[event_id, leg_id]`
- `ValuationRecord` rows sort by `[valuation_purpose, valued_at_or_null, valuation_id]`

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

- accepted event families stay jurisdiction-neutral and output-neutral
- event identity is driven by the selected semantic bundle, not by compilation
  bookkeeping noise
- event, leg, and valuation records carry the computation-critical
  determinants needed for later reconciliation, checkpointing, accounting, and
  tax
- corrections preserve supersession lineage instead of mutating accepted
  economic truth in place

Must not:

- collapse to spot-trade assumptions
- let output hints drive core behavior
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

- completeness, linkage, continuity, checkpoint candidates, and
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
- checkpoint candidacy derived from reconciled economics plus checkpoint
  evidence

Record families:

- `ContinuitySegmentRecord`
  - `continuity_segment_id`
  - `source`
  - `subject_ref`
  - `segment_start_at_or_null`
  - `segment_end_at_or_null`
  - `reconciliation_status`
  - `checkpoint_date_or_null`
- `LinkRecord`
  - `link_id`
  - `continuity_segment_id`
  - `link_kind`
  - `left_event_ref`
  - `right_event_ref`
  - `link_status`
- `BalanceTargetRecord`
  - `balance_target_id`
  - `continuity_segment_id`
  - `subject_ref`
  - `target_kind`
  - `target_as_of_at`
  - `expected_value`
  - `observed_value_or_null`
  - `balance_target_status`
- `CheckpointCandidateRecord`
  - `checkpoint_candidate_id`
  - `continuity_segment_id`
  - `subject_ref`
  - `checkpoint_date`
  - `candidate_status`
  - `supporting_balance_target_refs`
  - `supporting_evidence_refs`

Controlled vocabularies:

- `link_kind`:
  - `transfer_pair`
  - `settlement_pair`
- `link_status`:
  - `linked`
  - `candidate`
  - `blocked`
  - `superseded`
- `target_kind`:
  - `exact_balance`
  - `range_balance`
  - `continuity_anchor`
- `balance_target_status`:
  - `matched`
  - `mismatched`
  - `missing_observation`
  - `blocked`
- `candidate_status`:
  - `ready`
  - `partial`
  - `blocked`
  - `superseded`

Envelope or sidecar content may include:

- corroboration sidecars
- continuity explanation
- missing-leg detail
- comparison traces
- stage-owned gap and readiness sidecars

Product-root cardinality:

- one `ReconciliationState` kernel owns exactly one `ContinuitySegmentRecord`
- zero or more `LinkRecord`, `BalanceTargetRecord`, and
  `CheckpointCandidateRecord` rows may exist under that one continuity segment

Stable ids:

- `reconciliation_state_id` identifies one continuity-segment-scoped
  reconciliation kernel
- `continuity_segment_id` identifies one bounded continuity window
- `link_id` identifies one owned transfer or settlement linkage
- `balance_target_id` identifies one reconciliation-owned balance assertion
  target
- `checkpoint_candidate_id` identifies one reconciliation-owned checkpoint
  proposal
- `reconciliation_state_id` uses component array
  `[economic_facts_ref, continuity_segment_id]`
- `continuity_segment_id` uses component array
  `[source, subject_ref, segment_start_at_or_null, segment_end_at_or_null]`
- `link_id` uses component array
  `[continuity_segment_id, link_kind, left_event_ref, right_event_ref]`
- `balance_target_id` uses component array
  `[continuity_segment_id, subject_ref, target_kind, target_as_of_at, expected_value_fingerprint]`
- `checkpoint_candidate_id` uses component array
  `[continuity_segment_id, subject_ref, checkpoint_date, supporting_balance_target_refs]`
- `expected_value_fingerprint` is the canonical fingerprint of the
  `AssertionValue` carried in `expected_value`
- `supporting_evidence_refs` provide audit support, but they are not part of
  candidate identity

Ordering:

- `ContinuitySegmentRecord` rows sort by
  `[checkpoint_date_or_null, source, subject_ref, continuity_segment_id]`
- `LinkRecord` rows sort by
  `[continuity_segment_id, link_kind, left_event_ref, right_event_ref, link_id]`
- `BalanceTargetRecord` rows sort by
  `[continuity_segment_id, subject_ref, target_as_of_at, balance_target_id]`
- `CheckpointCandidateRecord` rows sort by
  `[checkpoint_date, subject_ref, continuity_segment_id, checkpoint_candidate_id]`

Serialization:

- serialize each reconciliation record family as its own ordered array
- persist product metadata once per emitted kernel
- use stable object-key ordering
- preserve the declared order above
- sort `supporting_balance_target_refs` and `supporting_evidence_refs`
  lexicographically

Fingerprint inputs:

- product metadata
- canonical `ContinuitySegmentRecord` rows
- canonical `LinkRecord` rows
- canonical `BalanceTargetRecord` rows
- canonical `CheckpointCandidateRecord` rows

Must guarantee:

- explicit completeness decisions
- explicit continuity decisions
- explicit missing-leg and missing-evidence surfaces
- preservation of partial truth when the whole window is not yet clean
- no rewriting of upstream economics to satisfy checks

Must not:

- reclassify upstream economics to make continuity easier
- bury missing evidence inside whole-dataset summaries
- use value refs that point to undefined payloads outside the kernel

Handoff to `Checkpoint`:

- `ReconciliationState` provides checkpoint candidates, corroboration,
  continuity outcomes, and reconciliation-owned blockers
- checkpoint acceptance still belongs to the checkpoint stage

## `Checkpoint`

Purpose:

- accepted checkpoint truth and acceptance basis

Product metadata:

- `checkpoint_run_id`
- `schema_version`
- `reconciliation_state_refs`
- `asserted_as_of_at`

Owns:

- accepted checkpoint assertions
- adopted opening state when intentionally used
- acceptance basis, trust level, and continuity into accepted state

Record families:

- `CheckpointRecord`
  - `checkpoint_id`
  - `asserted_as_of_at`
  - `ordered_checkpoint_assertion_ids`
- `CheckpointAssertionRecord`
  - `checkpoint_assertion_id`
  - `checkpoint_id`
  - `subject_ref`
  - `assertion_kind`
  - `asserted_as_of_at`
  - `accepted_value`
  - `trust_level`
  - `acceptance_basis`
  - `evidence_class`
  - `continuity_proof`
  - `checkpoint_candidate_refs`

Controlled vocabularies:

- `assertion_kind`:
  - `position_quantity`
  - `cash_quantity`
  - `basis_value`
  - `ownership_state`
  - `location_state`
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

Envelope or sidecar content may include:

- supporting evidence refs
- supporting provenance detail
- continuity explanation
- opening-state adoption detail
- acceptance rationale

Product-root cardinality:

- one `Checkpoint` kernel owns exactly one `CheckpointRecord`
- one or more `CheckpointAssertionRecord` rows may exist under that one
  checkpoint container

Stable ids:

- `checkpoint_run_id` identifies one accepted checkpoint kernel
- `checkpoint_id` identifies one accepted checkpoint container
- `checkpoint_assertion_id` identifies one accepted checkpoint truth record for
  one subject and one as-of point
- `checkpoint_run_id` uses component array
  `[ordered_reconciliation_state_refs, asserted_as_of_at]`
- `checkpoint_id` uses component array
  `[asserted_as_of_at, ordered_checkpoint_assertion_ids]`
- `checkpoint_assertion_id` uses component array
  `[assertion_kind, asserted_as_of_at, subject_ref, accepted_value_fingerprint]`
- `accepted_value_fingerprint` is the canonical fingerprint of one
  `AssertionValue` variant from [Domain Ontology](domain-ontology.md)

Ordering:

- `CheckpointRecord` rows sort by `[asserted_as_of_at, checkpoint_id]`
- `CheckpointAssertionRecord` rows sort by tuple
  `[asserted_as_of_at, subject_ref.subject_kind, subject_ref.subject_id, checkpoint_assertion_id]`

Serialization:

- serialize each checkpoint record family as its own ordered array
- persist product metadata once per emitted kernel
- use stable object-key ordering
- preserve the declared order above
- sort `checkpoint_candidate_refs` lexicographically

Lineage rule:

- `checkpoint_candidate_refs` uses ordered `checkpoint_candidate_id` values
  when reconciliation-owned candidates support the accepted assertion
- product-level `reconciliation_state_refs` remain the broader upstream
  partition lineage; assertion-level candidate refs point only at the accepted
  candidate path when that narrower lineage exists

Fingerprint inputs:

- product metadata
- canonical `CheckpointRecord` rows
- canonical `CheckpointAssertionRecord` rows

Minimum admissibility rules:

- `filing_ready` requires:
  - `acceptance_basis` other than `operator_assertion`
  - `evidence_class` other than `operator_assertion`
  - `continuity_proof` other than `partial_continuity`
- `analysis_ready` may use `operator_assertion` or `partial_continuity`, but
  the lower-trust basis stays explicit in the accepted checkpoint record
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

- `Checkpoint` provides accepted assertions, accepted opening state where used,
  and the acceptance basis
- downstream accounting and tax stages consume that accepted truth rather than
  re-deciding checkpoint trust locally

## `Journal`

Purpose:

- accounting expansion and validation over accepted truth

Product metadata:

- `journal_run_id`
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
  - `entry_kind`
  - `effective_at_or_null`
  - `economic_event_refs`
  - `checkpoint_assertion_refs`
  - `journal_status`
- `PostingRecord`
  - `posting_id`
  - `entry_id`
  - `account_ref`
  - `commodity_ref`
  - `amount`
  - `posting_side`
  - `origin_ref`
- `ValidationRecord`
  - `validation_id`
  - `entry_id`
  - `validation_kind`
  - `validation_status`
  - `blocking_gap_refs`

Controlled vocabularies:

- `entry_kind`:
  - `economic_event_entry`
  - `checkpoint_opening_entry`
  - `adjustment_entry`
- `posting_side`:
  - `debit`
  - `credit`
- `validation_kind`:
  - `balanced`
  - `commodity_balance`
  - `unsupported_coverage`
- `validation_status`:
  - `passed`
  - `blocked`

Envelope or sidecar content may include:

- posting explanation
- validation notes
- renderer-facing annotations
- accounting-owned gap sidecars

Product-root cardinality:

- one `Journal` kernel may contain many entries, postings, and validations
- one emitted `Journal` kernel must contain exactly one distinct `journal_id`

Stable ids:

- `journal_run_id` identifies one emitted `Journal` kernel
- `journal_id` identifies one accounting emission over a canonical set of
  upstream entries
- `entry_id` identifies one journal entry
- `posting_id` identifies one posting under one journal entry
- `validation_id` identifies one validation result under one journal entry
- `account_ref`, `commodity_ref`, and `origin_ref` use `AccountRef`,
  `CommodityRef`, and `OriginRef` from
  [Target Contract Primitives](../reference/target-contract-primitives.md)
- `journal_run_id` uses component array
  `[checkpoint_ref, ordered_economic_facts_refs]`
- `journal_id` uses component array
  `[ordered_economic_event_refs, ordered_checkpoint_assertion_refs, ordered_entry_kinds]`
- `entry_id` uses component array
  `[journal_id, entry_kind, effective_at_or_null, economic_event_refs, checkpoint_assertion_refs]`
- `posting_id` uses component array
  `[entry_id, account_ref, commodity_ref, amount, posting_side, origin_ref]`
- `validation_id` uses component array `[entry_id, validation_kind]`

Ordering:

- `JournalEntryRecord` rows sort by `[effective_at_or_null, entry_kind, entry_id]`
- `PostingRecord` rows sort by
  `[entry_id, posting_side, account_ref, commodity_ref, origin_ref, posting_id]`
- `ValidationRecord` rows sort by `[entry_id, validation_kind, validation_id]`

Serialization:

- serialize each journal record family as its own ordered array
- persist product metadata once per emitted kernel
- use stable object-key ordering
- preserve the declared order above
- sort `economic_event_refs`, `checkpoint_assertion_refs`, and
  `blocking_gap_refs` lexicographically

Fingerprint inputs:

- product metadata
- canonical `JournalEntryRecord` rows
- canonical `PostingRecord` rows
- canonical `ValidationRecord` rows

Must guarantee:

- deterministic posting expansion
- explicit validation
- explicit unsupported accounting coverage
- posting determinants required for validation remain part of the kernel

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

- tax determinants derived from reconciled economics plus accepted checkpoint
  truth
- explicit tax-owned blockers where upstream truth is still not tax-complete

Record families:

- `TaxDeterminantRecord`
  - `determinant_id`
  - `determinant_family`
  - `tax_year`
  - `basis_pool_ref`
  - `beneficial_owner_ref`
  - `instrument_ref`
  - `effective_at_or_null`
  - `quantity`
  - `direction`
  - `valuation_ref_or_null`
  - `counterparty_ref_or_null`
  - `economic_event_refs`
  - `checkpoint_assertion_refs`
  - `basis_transition_ref_or_null`
- `BasisTransitionRecord`
  - `basis_transition_id`
  - `basis_pool_ref`
  - `from_determinant_ref_or_null`
  - `to_determinant_ref`
  - `transition_kind`

Controlled vocabularies:

- `determinant_family`:
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
- `transition_kind`:
  - `pool_open`
  - `pool_adjustment`
  - `pool_close`
  - `carry_forward`

Envelope or sidecar content may include:

- tax-relevant valuation detail
- supporting ownership and counterparty context
- pool-transition explanation
- tax-owned blocker detail

Stable ids:

- `tax_inputs_id` identifies one emitted `TaxInputs` kernel
- `determinant_id` identifies one tax determinant
- `basis_transition_id` identifies one basis or pool transition
- `tax_inputs_id` uses component array
  `[checkpoint_ref, ordered_economic_facts_refs]`
- `determinant_id` uses component array
  `[tax_year, determinant_family, basis_pool_ref, beneficial_owner_ref, instrument_ref, effective_at_or_null, quantity, direction, economic_event_refs, checkpoint_assertion_refs]`
- `basis_transition_id` uses component array
  `[basis_pool_ref, transition_kind, from_determinant_ref_or_null, to_determinant_ref]`

Ordering:

- `TaxDeterminantRecord` rows sort by tuple
  `[tax_year, basis_pool_ref.tax_policy_id, basis_pool_ref.jurisdiction_or_regime, basis_pool_ref.beneficial_owner_ref, basis_pool_ref.pool_scope, determinant_family, effective_at_or_null, determinant_id]`
- `BasisTransitionRecord` rows sort by
  `[basis_pool_ref.tax_policy_id, basis_pool_ref.jurisdiction_or_regime, basis_pool_ref.beneficial_owner_ref, basis_pool_ref.pool_scope, transition_kind, basis_transition_id]`

Serialization:

- serialize each tax-input record family as its own ordered array
- persist product metadata once per emitted kernel
- use stable object-key ordering
- preserve the declared order above
- sort `economic_event_refs` and `checkpoint_assertion_refs` lexicographically

Fingerprint inputs:

- product metadata
- canonical `TaxDeterminantRecord` rows
- canonical `BasisTransitionRecord` rows

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
- push effective time, quantity, direction, or basis transitions into
  sidecars only

Handoff to `TaxOutputs`:

- `TaxInputs` provides the determinant surface that selected policies operate
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
- `policy_id`
- `tax_year`

Owns:

- policy-specific summaries, forms, schedules, and carry-forward state
- tax-policy explanations, limitations, and unsupported outputs
- tax-owned blockers that survive policy execution

Record families:

- `TaxOutputRecord`
  - `tax_output_id`
  - `policy_id`
  - `output_family`
  - `tax_year`
  - `tax_status`
  - `basis_pool_refs`
- `CarryForwardRecord`
  - `carry_forward_id`
  - `tax_output_id`
  - `basis_pool_ref`
  - `next_tax_year`
  - `state_fingerprint_ref`
- `UnsupportedItemRecord`
  - `unsupported_item_id`
  - `tax_output_id`
  - `determinant_ref`
  - `blocking_gap_refs`

Controlled vocabularies:

- `output_family`:
  - `realized_gains_schedule`
  - `income_schedule`
  - `expense_schedule`
  - `carry_forward_state`
  - `unsupported_items_report`

Envelope or sidecar content may include:

- policy-specific summaries
- schedules and forms
- carry-forward explanation
- unsupported-coverage notes

Product-root cardinality:

- one `TaxOutputs` kernel may contain many `TaxOutputRecord`,
  `CarryForwardRecord`, and `UnsupportedItemRecord` rows
- one emitted `TaxOutputs` kernel must contain exactly one `policy_id` and one
  `tax_year`

Stable ids:

- `tax_outputs_id` identifies one emitted `TaxOutputs` kernel
- `tax_output_id` identifies one policy-owned output emission
- `carry_forward_id` identifies one carry-forward state record
- `unsupported_item_id` identifies one persisted unsupported-item record
- `tax_outputs_id` uses component array `[tax_inputs_ref, policy_id, tax_year]`
- `tax_output_id` uses component array
  `[policy_id, output_family, tax_year, basis_pool_refs]`
- `carry_forward_id` uses component array
  `[tax_output_id, basis_pool_ref, next_tax_year]`
- `unsupported_item_id` uses component array
  `[tax_output_id, determinant_ref]`

Ordering:

- `TaxOutputRecord` rows sort by
  `[policy_id, tax_year, output_family, tax_output_id]`
- `CarryForwardRecord` rows sort by
  `[tax_output_id, next_tax_year, basis_pool_ref, carry_forward_id]`
- `UnsupportedItemRecord` rows sort by
  `[tax_output_id, determinant_ref, unsupported_item_id]`

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
- canonical `UnsupportedItemRecord` rows

Must guarantee:

- outputs are derived from `TaxInputs` through selected tax policies
- policy selection is explicit
- unsupported coverage stays explicit instead of being silently omitted

Must not:

- claim to come directly from `EconomicFacts` or `ReconciliationState`
- backfill earlier-stage semantic gaps by guessing
- claim to operate without accepted `EconomicFacts` and `Checkpoint` inputs

## Shared Contract References

The pipeline products rely on shared supporting contracts defined elsewhere:

- [Current Bridge Contracts](current-bridge-contracts.md) for the live bridge
  runtime truth
- [Bridge To Target Mapping](bridge-to-target-mapping.md) for the primary
  current-to-target transformation rules and migration authority matrix
- [First Slice Contract](../reference/first-slice-contract.md) for the bounded
  Coinbase-first replay and parity contract
- [First Downstream Slice Contract](../reference/first-downstream-slice-contract.md)
  for the first bounded `EconomicFacts -> ReconciliationState -> Checkpoint`
  contract
- [Domain Ontology](domain-ontology.md) for entity seams, refs,
  `AssertionValue`, and package ownership
- [Gaps And Readiness](gaps-and-readiness.md) for `GapCore`,
  `GapExplanation`, reviews, readiness, and `SubjectRef`
- [Reconciliation And Tax Architecture](reconciliation-tax-architecture.md) for
  persistence rules, partitioning rules, and fast-path expectations
