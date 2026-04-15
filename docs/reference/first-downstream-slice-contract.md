---
title: "First Downstream Slice Contract"
summary: "Bounded contract for the first Coinbase-first EconomicFacts, ReconciliationState, and Checkpoint slice, including bundle-based event identity and bridge compatibility projections."
doc_type: reference
audience: human
owner: repo
status: active
nav_order: 16
related:
  - docs/reference/first-slice-contract.md
  - docs/concepts/pipeline-stage-contracts.md
  - docs/concepts/domain-ontology.md
  - docs/concepts/reconciliation-tax-architecture.md
  - docs/status/migration-sequence.md
  - ROADMAP.md
---

Use this page when implementing or reviewing the first bounded downstream slice
after the default Coinbase-first `EvidenceSet -> ClaimSet` landing path. This
document freezes scope, ids, parity, replay, and allowed drift for the first
`EconomicFacts -> ReconciliationState -> Checkpoint` increment.

## Slice Scope

The first downstream slice is:

- the Coinbase-first slice already bounded by
  [First Slice Contract](first-slice-contract.md)
- accepted `EconomicFacts` emission for supported Coinbase retail activity and
  recognized statement-backed balance observations
- bounded `ReconciliationState` emission for continuity segments, exact balance
  targets, and checkpoint proposals over those in-scope economic facts
- bounded `Checkpoint` emission for statement-backed position-quantity
  assertions
- continued compatibility with current `TransactionFact`,
  `balance_snapshots.csv`, `balance_references.csv`, balance
  inspect/check/summarize flows, and `cointracking_csv`

The slice is not:

- a broad downstream migration for every source
- a replacement for `Journal`, `TaxInputs`, or `TaxOutputs`
- a claim that cross-source transfer pairing is already solved
- a claim that operator-only checkpoint inputs satisfy filing-ready truth

## In-Scope Record Families

The slice may emit only these downstream kernel families:

| Product | Record family | In-scope constraints |
| --- | --- | --- |
| `EconomicFacts` | `EconomicEventRecord` | only `asset_movement`, `cash_movement`, `fee_or_rebate`, and `correction` event kinds |
| `EconomicFacts` | `EconomicLegRecord` | only `holding_change`, `cash_change`, `fee`, and `rebate` leg roles |
| `EconomicFacts` | `ValuationRecord` | zero rows by default; valuations land only when an unchanged parity slice proves they are required |
| `ReconciliationState` | `ContinuitySegmentRecord` | one segment per in-scope Coinbase position subject and bounded time span |
| `ReconciliationState` | `BalanceTargetRecord` | only `kind = exact_balance`, with direct `expected_value` and `observed_value` using `AssertionValue` |
| `ReconciliationState` | `CheckpointProposalRecord` | only proposals supported by in-scope exact-balance targets and statement evidence |
| `Checkpoint` | `CheckpointRecord` | accepted root record for in-scope checkpoint assertions only |
| `Checkpoint` | `CheckpointAssertionRecord` | only `kind = position_quantity`, with direct `accepted_value` using `AssertionValue` |

`EventLinkRecord` remains out of scope for this bounded slice.

## Position And Subject Restrictions

The first downstream slice freezes one bounded position identity shape:

- `PositionRef = [beneficial_owner_ref, location_ref, instrument_ref, null, "custodial_spot_balance"]`

Rules:

- `beneficial_owner_ref` comes from in-scope `BeneficialOwnerClaim` output
- `location_ref` comes from in-scope `LocationClaim` output
- `instrument_ref` comes from in-scope `InstrumentIdentityClaim` output
- `contract_ref` stays `null` for this slice
- one continuity segment covers one `PositionRef`; do not mix positions into one
  segment
- when `SubjectRef` is needed for downstream attachment, the subject kind for
  this slice is `position`, pointing at the stable `PositionRef` identity

## Product Metadata And Compilation Inputs

In-scope product metadata fields:

- `EconomicFacts` carries `economic_facts_id`, `schema_version`, and
  `claim_set_refs`
- `ReconciliationState` carries `reconciliation_state_id`,
  `schema_version`, and `economic_facts_ref`
- `Checkpoint` carries `checkpoint_set_id`, `schema_version`,
  `reconciliation_state_refs`, and `as_of_at`

Compilation-input rules:

- downstream compilation consumes authoritative `ClaimBundleRecord`,
  `ClaimRecord`, `BundleDecisionRecord`, and `evidence_observation_refs`
  from authoritative `ClaimSet` kernels
- downstream compilation must not depend on `EconomicActivityDraft`,
  `SourceTranslationBatch`, or undeclared bridge hints as peer meaning inputs
- upstream `*_ref` metadata fields store target product ids, never `dataset_id`
  and never raw kernel fingerprints

## Kernel Cardinality And Ownership

Slice cardinality rules:

- one or more accepted `EconomicEventRecord` rows may be emitted from one
  accepted bundle
- one or more `EconomicLegRecord` rows may be emitted under one `event_id`
- zero `ValuationRecord` rows are expected by default in this slice
- one `ContinuitySegmentRecord` exists per in-scope `PositionRef` and bounded
  segment time span
- one or more `BalanceTargetRecord` rows may exist under one
  `continuity_segment_id`
- one or more `CheckpointProposalRecord` rows may exist under one
  `continuity_segment_id`
- one or more `CheckpointAssertionRecord` rows may exist under one
  `CheckpointRecord`

Ownership rules:

- `event_id` is derived from the selected claim bundle, not from
  adjudication bookkeeping
- `bundle_decision_id` may be referenced for audit, but it does not define
  event identity
- `BalanceTargetRecord` carries direct `AssertionValue` fields and must not
  point to undefined value refs or sidecars for hot-path meaning
- `CheckpointProposalRecord` identity is based on supporting balance-target
  refs, not incidental evidence-ref churn
- `CheckpointAssertionRecord` carries direct accepted truth and does not inherit
  authority from bridge balance references

## Id And Fingerprint Rules

Use the stable-id and fingerprint rules from
[Pipeline Stage Contracts](../concepts/pipeline-stage-contracts.md) unchanged.
This slice freezes the in-scope bounds and the first position identity shape.

Slice-specific rules:

- `economic_facts_id = [claim_set_refs]`
- `event_id = [bundle_id, event_index]`
- `leg_id = [event_id, role, subject_ref, leg_index]`
- `valuation_id = [source_ref, purpose, amount, currency, valued_at, valued_precision]`
- `reconciliation_state_id = [economic_facts_ref, continuity_segment_id]`
- `continuity_segment_id = [source_slug, subject_ref, segment_start_at, segment_end_at]`
- `balance_target_id = [continuity_segment_id, subject_ref, kind, as_of_at, expected_value_fingerprint]`
- `checkpoint_proposal_id = [continuity_segment_id, subject_ref, checkpoint_date, target_refs]`
- `checkpoint_set_id = [reconciliation_state_refs, as_of_at]`
- `checkpoint_assertion_id = [kind, as_of_at, subject_ref, accepted_value_fingerprint]`

Not allowed in this slice:

- event identity based on `bundle_decision_id` or rejected-bundle lists
- `expected_value_ref`
- `observed_value_ref`
- proposal ids that include raw evidence-ref lists as identity components

## Bridge Compatibility Projections

For in-scope subjects, the authoritative products after the slice are:

- `EconomicFacts` for accepted economic meaning
- `ReconciliationState` for continuity segments and balance targets
- `Checkpoint` for accepted checkpoint truth

Required derived compatibility projections:

- `TransactionFact` and related fact CSV outputs derived from `EconomicFacts`
  plus declared upstream claim compatibility sidecars when legacy hint
  reproduction still needs them
- `balance_snapshots.csv` derived from `ReconciliationState`
- `balance_references.csv` derived from `ReconciliationState`, `Checkpoint`,
  and declared support sidecars
- balance inspect/check/summarize outputs preserved through the active bridge
  compatibility surface until that application layer is repointed
- `cointracking_csv` preserved through the active output compatibility path

Compatibility rule:

- compatibility projections remain required during the migration window
- they are not authoritative for in-scope economic, reconciliation, or
  checkpoint truth once the target products exist
- retained legacy hint reproduction must come from declared compatibility
  sidecars, not from `EconomicActivityDraft`, `SourceTranslationBatch`, or
  bridge facts as peer economic authorities

## In-Scope Checkpoint Vocabulary

The first downstream slice allows only:

- `trust_level`:
  - `analysis_ready`
  - `filing_ready`
- `basis`:
  - `source_document`
  - `reconciled_continuity`
- `support_kind`:
  - `statement_balance`
- `continuity_proof`:
  - `direct_observation`
  - `reconciled_rollforward`

Not allowed in this slice:

- `operator_assertion`
- `adopted_opening_state`
- `platform_balance`
- `wallet_snapshot`
- `inventory_proof`
- `partial_continuity`

## Parity Gates

Unchanged first-slice inputs must preserve all of the following:

- accepted event ids and ordering
- accepted leg ids, ordering, and quantities
- `ContinuitySegmentRecord` ids and ordering
- `BalanceTargetRecord` ids, ordering, and statuses
- `CheckpointProposalRecord` ids, ordering, and statuses
- `CheckpointAssertionRecord` ids, ordering, and accepted values
- compiled `TransactionFact` ordering and semantics for in-scope evidence
- `balance_snapshots.csv` content for in-scope evidence
- `balance_references.csv` content for in-scope evidence
- balance inspect/check/summarize output for in-scope evidence
- `cointracking_csv` row ordering and field values

## Replay Gates

The slice is replay-safe only when repeated runs on unchanged evidence preserve:

- identical `EconomicFacts` kernel fingerprints
- identical `ReconciliationState` kernel fingerprints
- identical `Checkpoint` kernel fingerprints
- identical compiled bridge-fact fingerprints for in-scope evidence
- identical `balance_snapshots.csv` and `balance_references.csv` content for
  in-scope evidence
- identical balance inspect/check/summarize output for supported slice subjects
- identical `cointracking_csv` output for supported bridge facts

Replay checks must also prove that incidental input ordering changes do not
change event ids, leg ids, continuity segment ids, balance target ids,
checkpoint proposal ids, checkpoint assertion ids, or rendered output.

## Allowed Drift

Not allowed:

- drift in accepted economic kernel fields
- drift in continuity-segment, balance-target, checkpoint-proposal, or
  checkpoint-assertion ids
- quantity, accepted-value, trust-level, or acceptance-basis drift
- bridge-output drift on unchanged in-scope evidence
- balance inspect/check/summarize drift on unchanged in-scope evidence

Allowed only when kernel ids, statuses, and fingerprints stay unchanged:

- richer explanation text
- additional non-kernel gap, review, or readiness sidecars
- additional comparison detail that does not change product meaning

## Explicitly Out Of Scope

This bounded downstream slice does not:

- emit `EventLinkRecord` rows as a required success condition
- widen beyond the Coinbase-first slice already bounded by
  [First Slice Contract](first-slice-contract.md)
- make operator-only checkpoint acceptance part of the filing path
- use adopted opening state as an accepted checkpoint basis
- define runtime `Journal`, `TaxInputs`, or `TaxOutputs`
- require broad balance-provider hydration or cross-source transfer pairing
- authorize a repo-wide adapter migration before the bounded slice lands
