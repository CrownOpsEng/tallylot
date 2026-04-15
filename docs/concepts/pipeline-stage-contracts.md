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
  point here but should not restate competing kernel, id, or fingerprint
  contracts

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
- replay and parity gates operate on kernels first and inspect envelopes
  separately only where the slice requires them

## Shared Product Rules

Shared primitive and artifact authorities used by this page live in
[Target Contract Primitives](../reference/target-contract-primitives.md) and
[Target Product Artifacts](../reference/target-product-artifacts.md). This
page remains the owner of stage semantics, record families, stage-owned
vocabularies, and handoff guarantees.

### Versioning, Serialization, And Fingerprints

- every target product carries a `schema_version`
- `schema_version` is a product-level kernel field persisted once per emitted
  product beside the ordered kernel records for that product
- readers accept only the declared supported versions for that product
- unknown schema versions fail fast
- compatibility is forward-only by default; regeneration from upstream
  products or evidence is the normal recovery path for incompatible artifacts
- every target product defines one stable serialization and one stable
  fingerprint over semantically relevant kernel content
- kernel fingerprints use stable UTF-8 JSON serialization with stable object
  key order and declared array order, hashed with SHA-256
- fingerprints include semantically relevant upstream ids or upstream
  fingerprint references plus owning-stage decisions
- fingerprints exclude presentation-only formatting noise, explanation text,
  and sidecar payloads that do not change kernel meaning
- every stable id defined on this page uses the format
  `<kind>:<sha256(lowercase-hex)>`
- the hash input is one canonical UTF-8 JSON array of ordered components
- component arrays use the owning product's canonical scalar forms exactly as
  emitted; do not add hidden trimming, lowercasing, or resorting outside the
  declared tuple rules
- canonical scalar forms, admissible anchor components, shared dataset
  identity, reusable tuple contracts, and default target dataset packaging are
  owned by the reference pages above rather than redefined here

### Composite Tuple Rules

- `SubjectRef` serializes and sorts as `[subject_kind, subject_id]`
- `BasisPoolRef` serializes and sorts as
  `[tax_policy_id, jurisdiction_or_regime, beneficial_owner_ref, pool_scope]`
- plain `*_ref` and `*_refs` fields point to stable ids unless the owning page
  explicitly names a structured tuple contract such as `SubjectRef`,
  `BasisPoolRef`, `AccountRef`, `CommodityRef`, or `OriginRef`
- when one stable-id recipe, ordering rule, or fingerprint input includes one
  of these composite references, use the tuple form above rather than an
  object-name shorthand

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
- deterministic evidence-selection decisions
- typed provenance and locator identity for selected evidence
- source-local parsed observations that do not yet require economic meaning

Record families:

- `EvidenceRecord`
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

Envelope content may include:

- document metadata
- statement row detail
- inventory detail
- candidate-selection reasoning
- parse diagnostics
- rich provenance payloads

Stable ids:

- `evidence_set_id` identifies one bounded evidence emission for one source,
  adapter, capture, and selection-group scope
- `member_id` identifies one selected, superseded, or blocked evidence member
- `observation_id` identifies one typed observation under one evidence member
- `selection_group_id` identifies one deterministic evidence-selection
  decision boundary
- `evidence_set_id` uses component array
  `[source, adapter_id, capture_uid, selection_group_id]`
- `member_id` uses component array
  `[evidence_set_id, member_class, member_locator_identity]`
- `observation_id` uses component array
  `[member_id, observation_class, observation_anchor]`
- `selection_group_id` is emitted by the evidence-selection stage and remains a
  stable upstream id rather than a downstream recomputation; it is a
  decision-boundary id, not an evidence member family
- `member_class` is the stable evidence member-family or member-role label
  emitted for the member
- `member_locator_identity` is the stage-owned stable locator tuple for one
  evidence member
- `observation_class` is the stable typed observation label emitted for one
  observation under the owning evidence member
- `observation_anchor` is the stable row, page, anchor, or typed observation
  locator emitted for that observation

Ordering:

- sort by `source`
- then `capture_uid`
- then `selection_group_id`
- then `selection_status`
- then `member_id`
- then `observation_id`

Serialization:

- serialize `EvidenceRecord` rows only
- use stable object-key ordering
- preserve the declared evidence order above
- represent timestamps and `Decimal` values using the repo's stable string
  forms so the fingerprint is independent of language runtime defaults

Fingerprint inputs:

- canonical `EvidenceRecord` rows
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

Record families:

- `ClaimRecord`
  - `claim_set_id`
  - `claim_id`
  - `claim_family`
  - `claim_status`
  - `interpretation_group_id`
  - `evidence_member_refs`
  - `effective_at`
  - `effective_precision`
  - `provenance_refs`
- `CompilationDecisionRecord`
  - `claim_set_id`
  - `adjudication_record_id`
  - `interpretation_group_id`
  - `compilation_outcome`
  - `accepted_claim_refs`
  - `rejected_claim_refs`
  - `deferred_claim_refs`
  - `resolution_basis`
  - `blocking_gap_refs`

Envelope content may include:

- provider-local semantic detail
- comparison traces
- claim explanation
- advisory review payloads
- output-oriented annotations

### Minimum ClaimSet Taxonomy

This section is the sole owner of the shared minimum `ClaimSet` family
vocabulary.

| Claim family | Shared role | Default first-slice status |
| --- | --- | --- |
| `ActivityClaim` | provider-local activity or transaction meaning before shared compilation | in scope |
| `BalanceObservationClaim` | quantity-backed balance or as-of observation tied to evidence | in scope |
| `OwnershipClaim` | provider-local ownership or control assertion that may matter later | canonical but out of scope |
| `LocationClaim` | provider-local location or sub-location assertion | in scope |
| `StatementClaim` | parsed statement row or document-level semantic claim | canonical but out of scope |
| `InstrumentIdentityClaim` | provider-local instrument identity assertion | in scope |
| `ContractTermClaim` | provider-local term or contract assertion needed later | canonical but out of scope |
| `ValuationClaim` | valuation observation whose purpose affects later behavior | in scope |
| `ProjectionAnnotation` | output-oriented metadata that is not accepted economic truth | in scope |
| `IssueCandidate` | blocking pre-economic diagnostic candidate | in scope |
| `ReviewCandidate` | advisory pre-economic review candidate | in scope |

Rules:

- secondary docs may reference these claim families, but they must not publish
  competing repo-wide family lists
- later slices may use canonical families that are out of scope for the
  default first slice without redefining the shared vocabulary

Stable ids:

- `claim_set_id` identifies one bounded semantic emission over one evidence set
- `claim_id` identifies one claim family member with one stable semantic role
- `interpretation_group_id` identifies one mutually exclusive claim bundle
- `adjudication_record_id` identifies one compilation-decision record
- `claim_set_id` uses component array `[evidence_set_id, claim_emitter_id]`
- `claim_id` uses component array
  `[claim_set_id, claim_family, claim_anchor, interpretation_group_id]`
- `interpretation_group_id` uses component array
  `[claim_set_id, bundle_anchor, bundle_discriminator]`
- `adjudication_record_id` uses component array
  `[claim_set_id, interpretation_group_id, compilation_outcome, resolution_basis, accepted_claim_refs, rejected_claim_refs, deferred_claim_refs]`
- `claim_emitter_id` is the stable id of the translation family or shared
  compiler boundary that emitted the claim set; its reusable id recipe is
  owned by
  [Target Contract Primitives](../reference/target-contract-primitives.md)
- `claim_emitter_id` is product-scoped `ClaimSet` metadata, not an implicit
  local variable or adapter-private constant
- `claim_anchor` is the stable provider-local anchor for one asserted meaning;
  the shared admissibility rules for anchor components live in
  [Target Contract Primitives](../reference/target-contract-primitives.md),
  while slice-specific anchor choices live in
  [First Slice Contract](../reference/first-slice-contract.md)
- `bundle_anchor` is the stable anchor shared by all mutually exclusive bundles
  over the same source-local meaning; its admissibility rules also live in
  [Target Contract Primitives](../reference/target-contract-primitives.md)
- `bundle_discriminator` is `default` when one anchor has exactly one bundle;
  otherwise use `alt:1`, `alt:2`, and so on in canonical bundle order under
  that anchor

Controlled `resolution_basis` vocabulary:

- `single_bundle_match`
- `insufficient_identity`
- `insufficient_temporal_precision`
- `conflicting_claims`
- `upstream_blocker`
- `policy_deferred`
- `superseded_by_later_claims`

Ordering:

- `ClaimRecord` rows sort by tuple
  `[claim_family, effective_at_or_null, claim_id, interpretation_group_id]`
- use JSON `null` for `effective_at_or_null` when the claim has no effective
  time
- `CompilationDecisionRecord` rows sort by
  `[interpretation_group_id, adjudication_record_id]`

Serialization:

- serialize `ClaimRecord` rows and `CompilationDecisionRecord` rows as separate
  ordered arrays
- use stable object-key ordering
- preserve the declared claim and decision order above
- sort `evidence_member_refs`, `provenance_refs`, `accepted_claim_refs`,
  `rejected_claim_refs`, `deferred_claim_refs`, and `blocking_gap_refs`
  lexicographically

Fingerprint inputs:

- canonical `ClaimRecord` rows
- canonical `CompilationDecisionRecord` rows
- `schema_version`
- referenced `EvidenceSet` ids or fingerprints

Must guarantee:

- source-local semantics only
- preserved ambiguity where one safe final interpretation is unavailable
- provenance for every claim
- adapters may add provider-local subtyping, but they must preserve the shared
  claim-family distinctions so later compilation remains interoperable

Must not:

- force unresolved meaning into final economic or policy interpretations
- silently discard materially relevant alternative interpretations

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

Record families:

- `EconomicEventRecord`
  - `event_id`
  - `event_family`
  - `adjudication_record_id`
  - `accepted_claim_refs`
  - `effective_at`
  - `effective_precision`
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
  - `amount`
  - `currency`
  - `valuation_purpose`
  - `valued_at_or_null`
  - `value_precision_or_null`
  - `source_kind`
  - `confidence`
  - `provenance_refs`

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
- `valuation_purpose`:
  - `economic`
  - `checkpoint_support`
  - `accounting_support`
  - `tax_support`
  - `market_observation`

Envelope content may include:

- ownership and counterparty explanation
- explanation of accepted identity seams
- supporting claim traces
- review context carried forward for audit

Stable ids:

- `event_id` identifies one accepted economic event
- `leg_id` identifies one stable leg under one accepted event
- `valuation_id` identifies one persisted valuation kernel record
- `event_id` uses component array `[adjudication_record_id, event_index]`
- `leg_id` uses component array `[event_id, leg_role, subject_ref, leg_index]`
- `valuation_id` uses component array
  `[amount, currency, valuation_purpose, valued_at_or_null, value_precision_or_null, source_kind, confidence, provenance_refs]`
- `event_index` and `leg_index` are zero-based canonical positions in declared
  event and leg order
- `valuation_ref_or_null` points to `valuation_id` when a downstream stage
  must reason from persisted valuation truth instead of rehydrating envelope
  detail

Ordering:

- `EconomicEventRecord` rows sort by `effective_at` when present
- otherwise sort by `recorded_at`
- then `event_id`
- `EconomicLegRecord` rows sort by `[event_id, leg_id]`
- `ValuationRecord` rows sort by `[valuation_purpose, valued_at_or_null, valuation_id]`

Serialization:

- serialize `EconomicEventRecord`, `EconomicLegRecord`, and `ValuationRecord`
  rows as separate ordered arrays
- use stable object-key ordering
- preserve the declared event and leg order above
- sort `provenance_refs` lexicographically when a stronger stage-owned order is
  not declared

Fingerprint inputs:

- canonical `EconomicEventRecord` rows
- canonical `EconomicLegRecord` rows
- canonical `ValuationRecord` rows
- `schema_version`
- referenced `CompilationDecisionRecord` ids

Must guarantee:

- accepted event families stay jurisdiction-neutral and output-neutral
- event and leg records carry the computation-critical determinants needed for
  later reconciliation, checkpointing, accounting, and tax
- valuation records stay first-class kernel truth whenever later checkpoint,
  accounting, or tax behavior depends on them
- corrections preserve supersession lineage instead of mutating accepted
  economic truth in place
- unresolved economic detail may remain explicit only where later stages can
  still reason safely from the accepted kernel

Must not:

- collapse to spot-trade assumptions
- let output hints drive core behavior
- push leg quantity, location, or instrument truth into envelopes only

Handoff to `ReconciliationState`:

- `EconomicFacts` provides accepted economic events, economic legs, identity
  seams, settlement links, lifecycle state, and valuation records or
  references where they are already safe
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

Record families:

- `ContinuitySegmentRecord`
  - `continuity_segment_id`
  - `source`
  - `subject_ref`
  - `segment_start_at_or_null`
  - `segment_start_precision_or_null`
  - `segment_end_at_or_null`
  - `segment_end_precision_or_null`
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
  - `target_precision`
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

Envelope content may include:

- corroboration sidecars
- continuity explanation
- missing-leg detail
- comparison traces
- stage-owned gap and readiness sidecars

Stable ids:

- `continuity_segment_id` identifies one bounded continuity window
- `link_id` identifies one owned transfer or settlement linkage
- `balance_target_id` identifies one reconciliation-owned balance assertion
  target
- `checkpoint_candidate_id` identifies one reconciliation-owned checkpoint
  proposal
- `continuity_segment_id` uses component array
  `[source, subject_ref, segment_start_at_or_null, segment_start_precision_or_null, segment_end_at_or_null, segment_end_precision_or_null]`
- `link_id` uses component array
  `[continuity_segment_id, link_kind, left_event_ref, right_event_ref]`
- `balance_target_id` uses component array
  `[continuity_segment_id, subject_ref, target_kind, target_as_of_at, target_precision, expected_value_fingerprint]`
- `checkpoint_candidate_id` uses component array
  `[continuity_segment_id, subject_ref, checkpoint_date, supporting_balance_target_refs, supporting_evidence_refs]`
- `expected_value` and `observed_value_or_null` use the shared
  `AssertionValue` union owned by
  [Target Contract Primitives](../reference/target-contract-primitives.md)
- `expected_value_fingerprint` is the canonical fingerprint of one
  `AssertionValue` and keeps stable-id recipes on admissible scalar inputs
- reconciliation comparison values stay inline because they are
  kernel-critical determinants, not detachable sidecars
- `checkpoint_candidate_id` depends on supporting refs only; it does not
  include observed-value payloads or comparison text

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
- use stable object-key ordering
- preserve the declared order above
- sort `supporting_balance_target_refs` and `supporting_evidence_refs`
  lexicographically

Fingerprint inputs:

- canonical `ContinuitySegmentRecord` rows
- canonical `LinkRecord` rows
- canonical `BalanceTargetRecord` rows
- canonical `CheckpointCandidateRecord` rows
- `schema_version`
- referenced `EconomicFacts` ids or fingerprints

Must guarantee:

- explicit completeness decisions
- explicit continuity decisions
- explicit missing-leg and missing-evidence surfaces
- preservation of partial truth when the whole window is not yet clean
- no rewriting of upstream truth to satisfy checks

Must not:

- reclassify upstream economics to make continuity easier
- bury missing evidence inside whole-dataset summaries
- use stable-id recipes that depend on undeclared fields or hidden indexes

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
  - `reconciliation_refs`

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

Envelope content may include:

- supporting evidence refs
- supporting provenance detail
- continuity explanation
- opening-state adoption detail
- acceptance rationale

Stable ids:

- `checkpoint_id` identifies one accepted checkpoint container
- `checkpoint_assertion_id` identifies one accepted checkpoint truth record for
  one subject and one as-of point
- `checkpoint_id` uses component array
  `[asserted_as_of_at, ordered_checkpoint_assertion_ids]`
- `checkpoint_assertion_id` uses component array
  `[assertion_kind, asserted_as_of_at, subject_ref, accepted_value_fingerprint]`
- `accepted_value_fingerprint` is the canonical fingerprint of one
  `AssertionValue` from
  [Target Contract Primitives](../reference/target-contract-primitives.md)

Ordering:

- `CheckpointRecord` rows sort by `[asserted_as_of_at, checkpoint_id]`
- `CheckpointAssertionRecord` rows sort by tuple
  `[asserted_as_of_at, subject_ref.subject_kind, subject_ref.subject_id, checkpoint_assertion_id]`

Serialization:

- serialize `CheckpointRecord` rows and `CheckpointAssertionRecord` rows as
  separate ordered arrays
- use stable object-key ordering
- preserve the declared checkpoint order above
- sort `reconciliation_refs` lexicographically

Fingerprint inputs:

- canonical `CheckpointRecord` rows
- canonical `CheckpointAssertionRecord` rows
- `schema_version`
- referenced `ReconciliationState` ids or fingerprints
- referenced accepted evidence ids
- referenced opening-state ids when adoption is used

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

Record families:

- `JournalEntryRecord`
  - `journal_id`
  - `entry_id`
  - `entry_kind`
  - `effective_at`
  - `effective_precision`
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

Envelope content may include:

- posting explanation
- validation notes
- renderer-facing annotations
- accounting-owned gap sidecars

Stable ids:

- `journal_id` identifies one accounting emission over a canonical set of
  upstream entries
- `entry_id` identifies one journal entry
- `posting_id` identifies one posting under one journal entry
- `validation_id` identifies one validation result under one journal entry
- `journal_id` uses component array
  `[ordered_economic_event_refs, ordered_checkpoint_assertion_refs, ordered_entry_kinds]`
- `entry_id` uses component array
  `[journal_id, entry_kind, effective_at_or_null, economic_event_refs, checkpoint_assertion_refs]`
- `posting_id` uses component array
  `[entry_id, account_ref, commodity_ref, amount, posting_side, origin_ref]`
- `validation_id` uses component array `[entry_id, validation_kind]`
- `ordered_economic_event_refs`, `ordered_checkpoint_assertion_refs`, and
  `ordered_entry_kinds` are the canonical flattened journal-level arrays
  derived from the emitted `JournalEntryRecord` rows
- `account_ref`, `commodity_ref`, and `origin_ref` use the structured tuple
  contracts owned by
  [Target Contract Primitives](../reference/target-contract-primitives.md)
- `origin_ref` points to the immediate kernel origin for the posting rather
  than to a provider label, renderer label, or free-form source string

Ordering:

- `JournalEntryRecord` rows sort by `[effective_at_or_null, entry_kind, entry_id]`
- `PostingRecord` rows sort by
  `[entry_id, posting_side, account_ref, commodity_ref, posting_id]`
- `ValidationRecord` rows sort by `[entry_id, validation_kind, validation_id]`

Serialization:

- serialize each journal record family as its own ordered array
- use stable object-key ordering
- preserve the declared order above
- sort `economic_event_refs`, `checkpoint_assertion_refs`, and
  `blocking_gap_refs` lexicographically

Fingerprint inputs:

- canonical `JournalEntryRecord` rows
- canonical `PostingRecord` rows
- canonical `ValidationRecord` rows
- `schema_version`
- referenced `EconomicFacts` ids
- referenced `Checkpoint` assertion ids

Must guarantee:

- deterministic posting expansion
- explicit validation
- explicit unsupported accounting coverage
- posting determinants required for validation remain part of the kernel

Must not:

- become a truth repair layer
- hide postings or validation blockers in envelopes only

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

Record families:

- `TaxDeterminantRecord`
  - `determinant_id`
  - `determinant_family`
  - `tax_year`
  - `basis_pool_ref`
  - `beneficial_owner_ref`
  - `instrument_ref`
  - `effective_at`
  - `effective_precision`
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

Envelope content may include:

- tax-relevant valuation detail
- supporting ownership and counterparty context
- pool-transition explanation
- tax-owned blocker detail

Stable ids:

- `determinant_id` identifies one tax determinant
- `basis_transition_id` identifies one basis or pool transition
- `determinant_id` uses component array
  `[tax_year, determinant_family, basis_pool_ref, beneficial_owner_ref, instrument_ref, effective_at_or_null, effective_precision_or_null, quantity, direction, economic_event_refs, checkpoint_assertion_refs]`
- `basis_transition_id` uses component array
  `[basis_pool_ref, transition_kind, from_determinant_ref_or_null, to_determinant_ref]`

Ordering:

- `TaxDeterminantRecord` rows sort by tuple
  `[tax_year, basis_pool_ref.tax_policy_id, basis_pool_ref.jurisdiction_or_regime, basis_pool_ref.beneficial_owner_ref, basis_pool_ref.pool_scope, determinant_family, effective_at_or_null, determinant_id]`
- `BasisTransitionRecord` rows sort by
  `[basis_pool_ref.tax_policy_id, basis_pool_ref.jurisdiction_or_regime, basis_pool_ref.beneficial_owner_ref, basis_pool_ref.pool_scope, transition_kind, basis_transition_id]`

Serialization:

- serialize `TaxDeterminantRecord` rows and `BasisTransitionRecord` rows as
  separate ordered arrays
- use stable object-key ordering
- preserve the declared determinant and transition order above
- sort `economic_event_refs` and `checkpoint_assertion_refs` lexicographically

Fingerprint inputs:

- canonical `TaxDeterminantRecord` rows
- canonical `BasisTransitionRecord` rows
- `schema_version`
- referenced `EconomicFacts` ids
- referenced `Checkpoint` assertion ids

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
  envelopes only

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

Record families:

- `TaxOutputRecord`
  - `tax_output_id`
  - `tax_policy_id`
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

Envelope content may include:

- policy-specific summaries
- schedules and forms
- carry-forward explanation
- unsupported-coverage notes

Stable ids:

- `tax_output_id` identifies one policy-owned output emission
- `carry_forward_id` identifies one carry-forward state record
- `unsupported_item_id` identifies one persisted unsupported-item record
- `tax_output_id` uses component array
  `[tax_policy_id, output_family, tax_year, basis_pool_refs]`
- `carry_forward_id` uses component array
  `[tax_output_id, basis_pool_ref, next_tax_year]`
- `unsupported_item_id` uses component array
  `[tax_output_id, determinant_ref]`
- `tax_policy_id` uses the reusable `TaxPolicyId` contract owned by
  [Target Contract Primitives](../reference/target-contract-primitives.md)

Ordering:

- `TaxOutputRecord` rows sort by
  `[tax_policy_id, tax_year, output_family, tax_output_id]`
- `CarryForwardRecord` rows sort by
  `[tax_output_id, next_tax_year, basis_pool_ref, carry_forward_id]`
- `UnsupportedItemRecord` rows sort by
  `[tax_output_id, determinant_ref, unsupported_item_id]`

Serialization:

- serialize each tax-output record family as its own ordered array
- use stable object-key ordering
- preserve the declared order above
- sort `basis_pool_refs` and `blocking_gap_refs` lexicographically

Fingerprint inputs:

- canonical `TaxOutputRecord` rows
- canonical `CarryForwardRecord` rows
- canonical `UnsupportedItemRecord` rows
- `schema_version`
- referenced `TaxInputs` ids or fingerprints
- selected `tax_policy_id`

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
- [First Downstream Slice Contract](../reference/first-downstream-slice-contract.md)
  for the first bounded `EconomicFacts -> ReconciliationState -> Checkpoint`
  contract
- [Target Contract Primitives](../reference/target-contract-primitives.md) for
  canonical scalar forms, reusable tuple contracts, shared `AssertionValue`,
  and reusable target ids
- [Target Product Artifacts](../reference/target-product-artifacts.md) for
  target dataset packaging, kernel filenames, and sidecar locations
- [Domain Ontology](domain-ontology.md) for the target ontology and identity
  seams
- [Gaps And Readiness](gaps-and-readiness.md) for `GapCore`,
  `GapExplanation`, readiness, and `SubjectRef`
- [Reconciliation And Tax Architecture](reconciliation-tax-architecture.md) for
  performance rules, partitioning rules, and filing-critical acceptance
