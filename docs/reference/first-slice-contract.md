---
title: "First Slice Contract"
summary: "Bounded contract for the default Coinbase-first proto-EvidenceSet and proto-ClaimSet increment."
doc_type: reference
audience: human
owner: repo
status: active
nav_order: 15
related:
  - docs/concepts/bridge-to-target-mapping.md
  - docs/concepts/pipeline-stage-contracts.md
  - docs/status/adapter-delivery-plan.md
  - ROADMAP.md
---

Use this page when implementing or reviewing the default first vertical slice.
This document freezes scope, ids, fingerprints, replay, parity, and allowed
drift for the bounded Coinbase-first landing path.

## Slice Scope

The default first slice is:

- planner-enabled Coinbase retail CSV evidence selection
- recognized Coinbase statement-backed balance observation flow
- bounded proto-`EvidenceSet` and proto-`ClaimSet` emission for that family
- continued interoperability with current `SourceTranslationBatch`,
  `TransactionFact`, `balance_references.csv`, and `cointracking_csv`

The slice is not:

- the actual filing adapter inventory for `2023` to `2025`
- a repo-wide claim migration
- a broad unified-adapter facet rollout
- a replacement for `EconomicFacts`, `ReconciliationState`, or `Checkpoint`

## Evidence Families

The slice recognizes only these evidence families:

| Evidence family | Meaning | Required kernel role |
| --- | --- | --- |
| `coinbase_retail_export` | planner-selected Coinbase retail CSV member chosen for translation | selected, superseded, or blocked planner member |
| `coinbase_statement_document` | recognized Coinbase statement PDF document used for statement-backed quantity observation | selected evidence member with document identity |
| `coinbase_statement_balance_row` | one parsed statement quantity row from a recognized Coinbase statement document | evidence observation keyed to the owning document and row anchor |
| `coinbase_translation_selection_group` | deterministic planner decision boundary for one retail export family selection | bounded `selection_group_id` for the slice |

## Claim Families

The first slice may emit only these claim families:

| Claim family | Meaning in the slice |
| --- | --- |
| `ActivityClaim` | provider-local activity assertion derived from selected Coinbase retail rows |
| `BalanceObservationClaim` | quantity-backed balance or as-of observation derived from recognized statement rows |
| `InstrumentIdentityClaim` | provider-local asset identity assertion tied to one activity or statement observation |
| `LocationClaim` | provider-local claim about the Coinbase-held location or sub-location in scope |
| `ValuationClaim` | valuation observation preserved when downstream behavior depends on it |
| `ProjectionAnnotation` | output-oriented metadata that is not accepted economic truth |
| `IssueCandidate` | blocking pre-economic diagnostic candidate for later issue or gap assembly |
| `ReviewCandidate` | advisory pre-economic review candidate |

## Kernel Schemas

### Proto-`EvidenceSet`

Kernel fields for the bounded slice:

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

Required status vocabulary:

- `selected`
- `superseded`
- `blocked`

### Proto-`ClaimSet`

Kernel fields for the bounded slice:

- `claim_set_id`
- `claim_id`
- `claim_family`
- `claim_status`
- `interpretation_group_id`
- `evidence_member_refs`
- `effective_at`
- `effective_precision`
- `provenance_refs`

Required status vocabulary:

- `asserted`
- `blocked`
- `advisory`
- `superseded`

### Bridge Interop Outputs

The slice must continue to produce the current bridge interop outputs without
inventing new bridge-only schemas:

- `SourceTranslationBatch`
- compiled `TransactionFact` records
- `balance_references.csv`
- `cointracking_csv` rows through current renderer boundaries

## Id And Fingerprint Rules

Id rules:

- `evidence_set_id` is deterministic from `source`, `adapter_id`, `capture_uid`,
  and one stable `selection_group_id`
- `member_id` is deterministic from evidence provenance, member identity, and
  the selected evidence family
- `observation_id` is deterministic from `member_id` plus the row, page, or
  anchor identity for the observation
- `claim_set_id` is deterministic from `evidence_set_id` plus the claim-emitting
  translation family for the slice
- `claim_id` is deterministic from `claim_family`, provider-local operation or
  row grouping identity, and `interpretation_group_id`
- `interpretation_group_id` is deterministic from one mutually exclusive claim
  bundle; independent bundles must not share a group id

Fingerprint rules:

- kernel fingerprints use stable UTF-8 JSON serialization with stable object
  key order and declared array order, hashed with SHA-256
- product fingerprints include semantically relevant upstream ids or
  fingerprint references, not duplicated upstream payload blobs
- manifest fingerprints are referenced as upstream inputs; they are not
  duplicated into the emitted product kernel
- sidecars, explanations, and reviews use separate fingerprints when persisted
  independently

## Parity Gates

Unchanged evidence must preserve all of the following:

- selected evidence membership
- superseded and blocked candidate membership
- evidence member ids and observation ids
- claim ids and claim ordering
- timestamps and temporal precision
- quantities and sign
- bridge leg shapes
- balance reference kinds
- compiled `TransactionFact` ordering and semantics
- `cointracking_csv` row ordering and field values

## Replay Gates

The slice is replay-safe only when repeated runs on unchanged evidence preserve:

- identical planner-selected, superseded, and blocked partitions
- identical statement recognition outcomes
- identical proto-`EvidenceSet` and proto-`ClaimSet` kernel fingerprints
- identical compiled bridge fact fingerprints
- identical `balance_references.csv` content for in-scope evidence
- identical `cointracking_csv` output for supported bridge facts

Replay checks must also prove that incidental input ordering changes do not
change selected evidence membership, claim order, compiled bridge facts, or
rendered output.

## Allowed Drift

Not allowed:

- kernel-field drift in selected evidence membership
- kernel-field drift in claim ids or order
- timestamp or precision drift
- quantity drift
- leg-shape drift
- balance-reference-kind drift
- compiled bridge fact drift
- `cointracking_csv` row drift

Allowed only when kernel ids, statuses, and fingerprints stay unchanged:

- richer explanation text
- additional non-kernel envelope fields
- additional sidecar detail that does not change product meaning

## Explicitly Out Of Scope

This bounded slice does not:

- pin the real filing workspace adapter inventory for `2023` to `2025`
- widen beyond the Coinbase retail export family and recognized Coinbase
  statement balance observations
- define final `EconomicFacts`, `ReconciliationState`, `Checkpoint`,
  `Journal`, or `TaxInputs` runtime products
- force a repo-wide adapter-facet migration
- authorize broad target package scaffolding before the Phase 0 contract lock
  completes
