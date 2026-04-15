---
title: "First Slice Contract"
summary: "Bounded contract for the default Coinbase-first EvidenceSet and ClaimSet slice, including cardinality, ids, replay gates, and bridge compatibility projections."
doc_type: reference
audience: human
owner: repo
status: active
nav_order: 15
related:
  - docs/concepts/bridge-to-target-mapping.md
  - docs/concepts/pipeline-stage-contracts.md
  - docs/concepts/domain-ontology.md
  - docs/concepts/gaps-and-readiness.md
  - docs/status/adapter-delivery-plan.md
  - ROADMAP.md
---

Use this page when implementing or reviewing the default first vertical slice.
This document freezes scope, cardinality, ids, parity, replay, and allowed drift
for the bounded Coinbase-first `EvidenceSet -> ClaimSet` landing path.

## Slice Scope

The default first slice is:

- deterministic Coinbase retail CSV evidence selection
- recognized Coinbase statement document selection
- statement-backed balance-row observations under selected statement documents
- bounded `EvidenceSet` emission for that slice
- bounded `ClaimSet` emission for that slice
- continued compatibility with current `translation_input_plan.json`,
  `EconomicActivityDraft`, `SourceTranslationBatch`, compiled
  `TransactionFact`, `balance_references.csv`, and `cointracking_csv`

The slice is not:

- the actual filing adapter inventory for `2023` to `2025`
- a repo-wide claim migration
- a replacement for `EconomicFacts`, `ReconciliationState`, or `Checkpoint`
- a broad unified-adapter facet rollout

## `EvidenceSet` Coverage

The bounded slice may emit only these evidence member kinds:

| Evidence member kind | Meaning |
| --- | --- |
| `coinbase_retail_export` | one Coinbase retail CSV member under deterministic retail-export selection |
| `coinbase_statement_document` | one recognized Coinbase statement PDF document under per-document selection |

The bounded slice may emit only these observation kinds:

| Observation kind | Meaning | Owning member kind |
| --- | --- | --- |
| `statement_document` | recognized statement document detail preserved under the selected document member | `coinbase_statement_document` |
| `coinbase_statement_balance_row` | one parsed statement quantity row keyed to the owning statement document and row key | `coinbase_statement_document` |

Frozen kind-specific observation fields:

| Observation kind | Frozen kernel fields |
| --- | --- |
| `statement_document` | `statement_kind`, `document_effective_at`, `document_effective_precision`, `statement_as_of_at`, `statement_as_of_precision` |
| `coinbase_statement_balance_row` | `account_label`, `wallet_label`, `balance_kind`, `asset_symbol`, `quantity`, `observed_at`, `observed_precision`, `notes`, `staked_quantity_text`, `value_amount_text`, `value_currency`, `price_amount_text`, `price_currency` |

Observation-field rules:

- there is no retail-row observation kind in this bounded pass
- `statement_document.statement_kind` uses the recognized statement-adapter kind
  for the selected document member
- `statement_document.statement_as_of_at` and `document_effective_at` lift the
  current parsed statement times, and the paired `*_precision` fields follow
  the repo-wide temporal
  precision contract
- `coinbase_statement_balance_row` lifts account, wallet, balance kind, asset,
  quantity, as-of time, and optional note or valuation text directly from the
  current statement-row contract
- `statement_document` may leave shell `observed_at` or
  `observed_precision` empty when the kind-specific document timing
  fields carry the truthful time meaning
- no generic observation payload blob is allowed for in-scope kinds

The bounded slice uses only these selection keys:

| `key` | Meaning |
| --- | --- |
| `["coinbase_retail_export"]` | deterministic decision boundary for Coinbase retail export selection |
| `["statement_document", locator]` | deterministic inclusion decision for one recognized statement document |

`translation_input_candidates.json` remains envelope or sidecar reasoning only.
It does not become a kernel record family.

## `ClaimSet` Coverage

The bounded slice may emit only this in-scope subset of claim kinds:

| Claim kind | Meaning in the slice |
| --- | --- |
| `ActivityClaim` | source-local activity assertion derived from selected Coinbase retail rows |
| `BalanceObservationClaim` | quantity-backed balance observation derived from recognized statement rows |
| `InstrumentIdentityClaim` | asset identity assertion tied to one activity or statement observation |
| `LocationClaim` | assertion about the Coinbase-held location or sub-location in scope |
| `BeneficialOwnerClaim` | assertion for the beneficial owner needed by downstream position identity |
| `ValuationClaim` | canonically defined now but zero-row by default in this bounded slice |

Out of scope for this slice:

- `LegalOwnerClaim`
- `CounterpartyClaim`
- `StatementClaim`
- `ContractTermClaim`

Bridge or output annotation detail and gap or review helper detail are not
claim kinds and are never emitted by this slice.

Frozen kind-specific claim fields:

| Claim kind | Frozen kernel fields |
| --- | --- |
| `ActivityClaim` | `source_activity_kind`, `location_claim_ref`, `activity_leg_specs` |
| `BalanceObservationClaim` | `location_claim_ref`, `instrument_claim_refs`, `balance_kind`, `quantity`, `observed_at`, `observed_precision` |
| `InstrumentIdentityClaim` | `scheme`, `value`, `venue`, `kind_hint`, `display_name`, `precision_hint` |
| `LocationClaim` | `location_ref`, `account_label`, `wallet_label` |
| `BeneficialOwnerClaim` | `beneficial_owner_ref` |
| `ValuationClaim` | `measure_kind`, `purpose`, `amount`, `currency`, `valued_at`, `valued_precision`, `location_claim_ref`, `instrument_claim_refs` |

`activity_leg_specs` entry shape:

- `leg_slot`
- `leg_kind`
- `quantity`
- `instrument_claim_refs`
- `location_claim_ref`
- `subtype`
- `attributed_to_leg_slot`

Claim-field and linkage rules:

- `ActivityClaim.source_activity_kind` is the owning field for the current
  Coinbase retail transaction type in this bounded slice
- `activity_leg_specs` lift ordered leg meaning from the current draft-leg
  contract, including sign, subtype, optional attributed-leg linkage, and
  optional location
- retail activity claims use `evidence_member_refs` plus
  `[retail_member_id, raw_row_ref]` interpretation-scope keys
- statement-derived claims use both `evidence_member_refs` and
  `evidence_observation_refs`
- `BalanceObservationClaim` must include the row observation id and may also
  include the paired `statement_document` observation id
- `ValuationClaim` remains zero-row by default until a later owner-doc pass
  freezes numeric statement valuation inputs
- no generic claim payload blob is allowed for in-scope kinds

## Kernel Cardinality And Ownership

Slice cardinality rules:

- one `EvidenceSet` is emitted per
  `[source_slug, adapter_id, capture_uid, selection_fingerprint]`
- one `SelectionRecord` exists per `selection_id`
- one or more `EvidenceMemberRecord` rows may belong to one
  `selection_id`
- zero or more `EvidenceObservationRecord` rows may belong to one `member_id`
- one `ClaimSet` is emitted per `[evidence_set_id, claim_emitter_id]`
- one `interpretation_scope_id` exists per source-local claim scope
- one or more `ClaimBundleRecord` rows may exist per `interpretation_scope_id`
- one `BundleDecisionRecord` exists per `interpretation_scope_id`
- one or more `ClaimRecord` rows may exist per `bundle_id`

Ownership rules:

- `SelectionRecord` owns selection basis and blocking-gap refs only
- `EvidenceMemberRecord` owns selected, superseded, or blocked membership
- `BundleDecisionRecord` remains claim-owned and records bundle selection,
  deferral, blocking, or supersession only
- claim-stage gaps and reviews may attach to `interpretation_scope_id` when
  no narrower truthful subject has resolved yet
- `BundleDecisionRecord` must not carry event fields, leg fields, or
  other economic facts

## Bridge Compatibility Projections

For in-scope evidence, the first slice changes authority but preserves bridge
compatibility.

Authoritative products after the slice:

- `EvidenceSet` for evidence selection and typed observations
- `ClaimSet` for source-local meaning

Required derived compatibility projections:

- `translation_input_plan.json` derived from `EvidenceSet`
- `EconomicActivityDraft` derived from `ClaimSet` plus declared compatibility
  sidecars keyed by `claim_id` or `bundle_id`
- `SourceTranslationBatch` derived from `ClaimSet` plus declared
  compatibility sidecars and shared support sidecars
- compiled `TransactionFact` rows preserved for current bridge consumers
- `balance_references.csv` preserved for current downstream compatibility
- `cointracking_csv` preserved through the active bridge/output path

Compatibility rule:

- bridge projections remain required during the compatibility window
- bridge projections are not authoritative for in-scope target meaning once
  `EvidenceSet` and `ClaimSet` exist

Declared compatibility-sidecar boundary:

- legacy bridge-only fields such as `economic_kind`, `projection_hint`,
  `accounting_intent_hint`, `tax_treatment_hint`, `description`,
  `tx_hash_or_null`, `operation_group_id_or_null`, `confidence`, and `status`
  stay outside `ClaimSet` kernels
- `provider_operation_key` stays satisfied by
  `ActivityClaim.source_activity_kind` and is not duplicated as a
  compatibility-only claim field

## Id And Fingerprint Rules

Use the stable-id and fingerprint rules from
[Pipeline Stage Contracts](../concepts/pipeline-stage-contracts.md) unchanged.
This slice only freezes the admissible keys and bounded vocabularies.

Slice-specific identity rules:

- `claim_emitter_id` is the shared emitter id over
  `[source_slug, adapter_id, "claim-compiler"]`
- `source_slug` uses the shared source slug across source-local
  products
- `evidence_set_id` intentionally changes when `selection_fingerprint`
  changes, because the authoritative capture-level evidence emission changed
- `locator` for `coinbase_retail_export` is
  `[raw_file, raw_member_ref]`
- `locator` for `coinbase_statement_document` is
  `[raw_file, raw_member_ref]`
- `key` for `statement_document` is `["document"]`
- `key` for `coinbase_statement_balance_row` is `[row_key]`
- `retail_member_id` means the `member_id` of the selected
  `coinbase_retail_export` member
- `document_member_id` means the `member_id` of the selected
  `coinbase_statement_document` member
- `raw_row_ref` means the stable retail-row reference preserved by the current
  Coinbase retail bridge inputs for one selected CSV row
- `row_key` means the stable statement-row key preserved on the
  `coinbase_statement_balance_row` observation

Slice-specific interpretation-scope keys:

- retail activity scope uses `[retail_member_id, raw_row_ref]`
- statement balance scope uses `[document_member_id, row_key]`

Slice-specific claim-key rule:

- `key` uses `[scope_key, kind, claim_slot]`
- `claim_slot` is `0` when only one claim of that kind exists in the bundle
- repeated same-kind claims use `1`, `2`, and so on in canonical order

Bundle rule:

- `key` is `default` when the scope has one bundle
- alternative bundles use `alt:1`, `alt:2`, and so on in canonical bundle
  order

## Parity Gates

Unchanged evidence must preserve all of the following:

- selected, superseded, and blocked evidence membership
- `selection_id`, `member_id`, and `observation_id`
- `claim_id`, `bundle_id`, and `bundle_decision_id`
- claim ordering and bundle ordering
- timestamps and temporal precision
- quantities and sign
- compiled `TransactionFact` ordering and semantics for in-scope evidence
- `balance_references.csv` content for in-scope evidence
- `cointracking_csv` row ordering and field values for supported projections

## Replay Gates

The slice is replay-safe only when repeated runs on unchanged evidence preserve:

- identical selected, superseded, and blocked retail-export partitions
- identical statement recognition outcomes
- identical `EvidenceSet` and `ClaimSet` kernel fingerprints
- identical derived bridge-fact fingerprints for in-scope evidence
- identical `balance_references.csv` content for in-scope evidence
- identical `cointracking_csv` output for supported bridge facts

Replay checks must also prove that incidental input ordering changes do not
change evidence selection, claim order, bundle order, bundle decisions, or
rendered output.

## Allowed Drift

Not allowed:

- kernel-field drift in selected evidence membership
- kernel-field drift in ids, statuses, ordering, or bundle structure
- timestamp or precision drift
- quantity drift
- derived bridge-fact drift on unchanged in-scope evidence
- `balance_references.csv` or `cointracking_csv` drift on unchanged in-scope
  evidence

Allowed only when kernel ids, statuses, and fingerprints stay unchanged:

- richer explanation text
- additional non-kernel envelope fields
- additional support sidecar detail that does not change product meaning

## Explicitly Out Of Scope

This bounded slice does not:

- pin the real filing workspace adapter inventory for `2023` to `2025`
- widen beyond Coinbase retail exports and recognized Coinbase statement
  balance observations
- define runtime `EconomicFacts`, `ReconciliationState`, `Checkpoint`,
  `Journal`, or `TaxInputs`
- authorize broad target package scaffolding before the contract-lock pass is
  complete
- require a repo-wide adapter-facet migration before the bounded slice lands
