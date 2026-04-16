---
title: "First Upstream Slice Contract"
summary: "Bounded contract for the first upstream `EvidenceSet -> ClaimSet` slice, scoped to Coinbase retail and statement evidence, including cardinality, ids, replay gates, and bridge compatibility projections."
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

Use this page when implementing or reviewing the first upstream slice.
This document freezes scope, cardinality, ids, parity, replay, and allowed
drift for the first upstream `EvidenceSet -> ClaimSet` landing path.

## Slice Scope

This slice is:

- deterministic Coinbase retail CSV evidence selection
- recognized Coinbase statement document selection
- statement-backed balance-row observations under selected statement documents
- bounded `EvidenceSet` emission for that slice
- bounded `ClaimSet` emission for that slice
- continued compatibility with current `translation_input_plan.json`,
  `EconomicActivityDraft`, `SourceTranslationBatch`,
  `TransactionFact`, `balance_references.csv`, and `cointracking_csv`

The slice is not:

- the actual filing adapter inventory for `2023` to `2025`
- a repo-wide claim migration
- a replacement for `EconomicFacts`, `ReconciliationState`, or `Checkpoint`
- a broad unified-adapter facet rollout

## `EvidenceSet` Coverage

This slice may emit only these evidence member kinds:

| Evidence member kind | Meaning |
| --- | --- |
| `coinbase_retail_export` | one Coinbase retail CSV member under deterministic retail-export selection |
| `coinbase_statement_document` | one recognized Coinbase statement PDF document under per-document selection |

This slice may emit only these observation kinds:

| Observation kind | Meaning | Owning member kind |
| --- | --- | --- |
| `statement_document` | recognized statement document detail preserved under the selected document member | `coinbase_statement_document` |
| `statement_balance_row` | one parsed statement quantity row keyed to the owning statement document and row key | `coinbase_statement_document` |

Frozen kind-specific observation fields:

| Observation kind | Frozen kernel fields |
| --- | --- |
| `statement_document` | `statement_kind`, `document_effective_at`, `document_effective_precision`, `statement_as_of`, `statement_as_of_precision` |
| `statement_balance_row` | `location_group_label`, `location_label`, `balance_kind`, `instrument_symbol`, `quantity`, `observed_at`, `precision`, `notes`, `staked_quantity_text`, `value_amount_text`, `value_currency`, `price_amount_text`, `price_currency` |

Observation-field rules:

- there is no retail-row observation kind in this pass
- `statement_document.statement_kind` uses the recognized statement-adapter kind
  for the selected document member
- `statement_document.statement_as_of` and `document_effective_at` lift the
  current parsed statement times, and the paired `*_precision` fields follow
  the repo-wide temporal
  precision contract
- `statement_balance_row` lifts location-group and location labels, balance
  kind, instrument, quantity, as-of time, and optional note or valuation text
  directly from the current statement-row contract
- `location_group_label` preserves the higher-scope source-provided grouping
  label, such as an account or custody container name, without freezing that
  source noun into the canonical target field list
- `location_label` preserves the source-provided lower-scope or direct
  location label, such as a source sub-location name, without freezing that
  source noun into the canonical target field list
- `statement_document` may leave shell `observed_at` or
  `precision` empty when the kind-specific document timing
  fields carry the truthful time meaning
- no generic observation payload blob is allowed for kinds in this slice

This slice uses only these selection keys:

| `key` | Meaning |
| --- | --- |
| `["coinbase_retail_export"]` | deterministic decision boundary for Coinbase retail export selection |
| `["statement_document", locator]` | deterministic inclusion decision for one recognized statement document |

`translation_input_candidates.json` remains planning-sidecar content only. It
does not become a kernel record family.

## `ClaimSet` Coverage

This slice may emit only this subset of `ClaimRecord.kind` values:

| Claim kind | Meaning in the slice |
| --- | --- |
| `activity` | evidence-local activity assertion derived from selected Coinbase retail rows |
| `balance` | quantity-backed balance claim derived from recognized statement rows |
| `instrument` | instrument assertion tied to one activity or statement observation |
| `location` | assertion about the in-scope custodial location or sub-location |
| `beneficial_owner` | assertion for the beneficial owner needed by downstream position identity |
| `valuation` | canonically defined now but zero-row by default in this slice |

Out of scope for this slice:

- `legal_owner`
- `counterparty`
- `statement_document`
- `contract`

Bridge or output annotation sidecar detail and gap, review, or readiness
sidecar content are not claim kinds and are never emitted by this slice.

Frozen kind-specific claim fields:

| Claim kind | Frozen kernel fields |
| --- | --- |
| `activity` | `activity_label`, `location_claim_ref`, `leg_specs` |
| `balance` | `location_claim_ref`, `instrument_claim_refs`, `balance_kind`, `quantity`, `observed_at`, `precision` |
| `instrument` | `scheme`, `value`, `venue`, `instrument_kind`, `name`, `precision` |
| `location` | `location_ref`, `location_group_label`, `location_label` |
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

Claim-field and linkage rules:

- `activity` claims own the current Coinbase retail `activity_label` in this
  slice
- `leg_specs` lift ordered leg meaning from the current draft-leg
  contract, including sign, subtype, optional attributed-leg linkage, and
  optional location
- retail claims with `kind = activity` use `member_refs` plus
  `[retail_member_id, raw_row_ref]` claim-scope keys
- statement-derived claims use both `member_refs` and
  `observation_refs`
- `balance` claims must include the row observation id and may also
  include the paired `statement_document` observation id
- `valuation` claims remain zero-row by default until a later owner-page pass
  freezes numeric statement valuation inputs
- `location` claims use `location_group_label` and `location_label` under the
  same target-contract rules as `statement_balance_row`: preserve the
  source-provided higher-scope and lower-scope labels, but keep the canonical
  target nouns aligned to `Location`
- no generic claim payload blob is allowed for kinds in this slice

## Kernel Cardinality And Ownership

Slice cardinality rules:

- one `EvidenceSet` is emitted per
  `[source_slug, adapter_id, capture_uid, selection_fingerprint]`
- one `EvidenceSelectionRecord` exists per `selection_id`
- one or more `EvidenceMemberRecord` rows may belong to one
  `selection_id`
- zero or more `EvidenceObservationRecord` rows may belong to one `member_id`
- one `ClaimSet` is emitted per `[evidence_set_id, emitter_id]`
- one `claim_scope_id` exists per evidence-local scope
- one or more `ClaimBundleRecord` rows may exist per `claim_scope_id`
- one `ClaimBundleDecisionRecord` exists per `claim_scope_id`
- one or more `ClaimRecord` rows may exist per `claim_bundle_id`

Ownership rules:

- `EvidenceSelectionRecord` owns selection basis and blocking-gap refs only
- `EvidenceMemberRecord` owns selected, superseded, or blocked membership
- `ClaimBundleDecisionRecord` remains claim-owned and records claim-bundle
  selection, deferral, blocking, or supersession only
- claim-stage gaps and reviews may attach to `claim_scope_id` when
  no narrower truthful subject has resolved yet
- `ClaimBundleDecisionRecord` must not carry event fields, leg fields, or
  other economic facts

## Bridge Compatibility Projections

For evidence in this slice, the first upstream slice changes authority but
preserves bridge compatibility.

Authoritative products after the slice:

- `EvidenceSet` for evidence selection and typed observations
- `ClaimSet` for evidence-local meaning

Required derived compatibility projections:

- `translation_input_plan.json` derived from `EvidenceSet`
- `EconomicActivityDraft` derived from `ClaimSet` plus declared compatibility
  sidecars keyed by `claim_id` or `claim_bundle_id`
- `SourceTranslationBatch` derived from `ClaimSet` plus declared
  compatibility sidecars and shared gap/review/readiness sidecars
- derived `TransactionFact` rows preserved for current bridge consumers
- `balance_references.csv` preserved for current downstream compatibility
- `cointracking_csv` preserved through the active bridge/output path

Compatibility rule:

- bridge projections remain required during the compatibility window
- bridge projections are not authoritative for target meaning in this slice once
  `EvidenceSet` and `ClaimSet` exist

Declared compatibility sidecar boundary:

- legacy bridge-only fields such as `economic_kind`, `projection_hint`,
  `accounting_intent_hint`, `tax_treatment_hint`, `description`,
  `tx_hash_or_null`, `operation_group_id_or_null`, `confidence`, and `status`
  stay outside `ClaimSet` kernels
- legacy `provider_operation_key` stays satisfied by
  `activity_label` on claims with `kind = activity` and is not duplicated as a
  compatibility-only claim field

## Id And Fingerprint Rules

Use the stable-id and fingerprint rules from
[Pipeline Stage Contracts](../concepts/pipeline-stage-contracts.md) unchanged.
This slice only freezes the admissible keys and bounded vocabularies.

Slice-specific identity rules:

- `emitter_id` is the shared emitter id over
  `[source_slug, adapter_id, "claim"]`
- `source_slug` stays the same across evidence-local products
- `evidence_set_id` intentionally changes when `selection_fingerprint`
  changes, because the authoritative capture-level evidence emission changed
- `locator` for `coinbase_retail_export` is
  `[raw_file, raw_member_ref]`
- `locator` for `coinbase_statement_document` is
  `[raw_file, raw_member_ref]`
- `key` for `statement_document` is `["document"]`
- `key` for `statement_balance_row` is `[row_key]`
- `retail_member_id` means the `member_id` of the selected
  `coinbase_retail_export` member
- `document_member_id` means the `member_id` of the selected
  `coinbase_statement_document` member
- `raw_row_ref` means the stable retail-row reference preserved by the current
  Coinbase retail bridge inputs for one selected CSV row
- `row_key` means the stable statement-row key preserved on the
  `statement_balance_row` observation

Slice-specific scope keys:

- retail activity scope uses `[retail_member_id, raw_row_ref]`
- statement balance scope uses `[document_member_id, row_key]`

Slice-specific claim-key rule:

- `key` uses `[scope_key, kind, slot]`
- `slot` is `0` when only one claim of that kind exists in the bundle
- repeated same-kind claims use `1`, `2`, and so on in canonical order

Bundle rule:

- `key` is `default` when the scope has one bundle
- alternative bundles use `alt:1`, `alt:2`, and so on in canonical bundle
  order

## Parity Gates

Retained compatibility projections are part of the slice parity bar. Kernel
parity alone is not sufficient while these legacy readers remain active.

Unchanged evidence must preserve all of the following:

- selected, superseded, and blocked evidence membership
- `selection_id`, `member_id`, and `observation_id`
- `claim_id`, `claim_bundle_id`, and `claim_bundle_decision_id`
- claim ordering and bundle ordering
- timestamps and temporal precision
- quantities and sign
- `translation_input_plan.json` content
- `EconomicActivityDraft` ordering and content for evidence in this slice
- `SourceTranslationBatch` content for evidence in this slice
- derived `TransactionFact` ordering and meaning for evidence in this slice
- `balance_references.csv` content for evidence in this slice
- `cointracking_csv` row ordering and field values for supported projections

## Replay Gates

The slice is replay-safe only when repeated runs on unchanged evidence preserve:

- identical selected, superseded, and blocked retail-export partitions
- identical statement recognition outcomes
- identical `EvidenceSet` and `ClaimSet` kernel fingerprints
- identical `translation_input_plan.json` content
- identical `EconomicActivityDraft` content for evidence in this slice
- identical `SourceTranslationBatch` content for evidence in this slice
- identical derived `TransactionFact` fingerprints for evidence in this slice
- identical `balance_references.csv` content for evidence in this slice
- identical `cointracking_csv` output for supported bridge facts

Replay checks must also prove that incidental input ordering changes do not
change evidence selection, claim order, claim-bundle order,
claim-bundle decisions, or
rendered output.

## Allowed Drift

Not allowed:

- kernel-field drift in selected evidence membership
- kernel-field drift in ids, statuses, ordering, or claim-bundle structure
- timestamp or precision drift
- quantity drift
- `translation_input_plan.json`, `EconomicActivityDraft`, or
  `SourceTranslationBatch` drift on unchanged evidence in this slice
- derived `TransactionFact` drift on unchanged evidence in this slice
- `balance_references.csv` or `cointracking_csv` drift on unchanged evidence in
  this slice

Allowed only when kernel ids, statuses, and fingerprints stay unchanged:

- richer explanation text
- additional gap, review, readiness, or other sidecar detail that does not
  change product
  meaning

## Explicitly Out Of Scope

This slice does not:

- pin the real filing workspace adapter inventory for `2023` to `2025`
- widen beyond Coinbase retail exports and recognized Coinbase statement
  balance observations
- define runtime `EconomicFacts`, `ReconciliationState`, `Checkpoint`,
  `Journal`, or `TaxInputs`
- authorize broad target package scaffolding before the contract-lock pass is
  complete
- require a repo-wide adapter-facet migration before this slice lands
