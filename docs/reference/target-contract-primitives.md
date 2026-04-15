---
title: "Target Contract Primitives"
summary: "Shared scalar forms, tuple contracts, dataset ids, and reusable id helpers for forward-looking target products."
doc_type: reference
audience: human
owner: repo
status: active
nav_order: 17
related:
  - docs/concepts/pipeline-stage-contracts.md
  - docs/concepts/domain-ontology.md
  - docs/concepts/gaps-and-readiness.md
  - docs/reference/target-product-artifacts.md
  - ROADMAP.md
---

Use this page when a forward-looking target contract needs a canonical scalar,
tuple, anchor, or reusable identity rule. This page owns those shared contract
primitives so later implementation slices do not invent local wire shapes.

## Purpose And Scope

This page owns:

- canonical scalar forms used by forward-looking target products
- tuple and structured-ref contracts reused across target stages
- anchor admissibility rules for stable ids and fingerprints
- shared dataset identity
- reusable id helpers such as `claim_emitter_id` and `TaxPolicyId`
- the shared `AssertionValue` union reused by reconciliation and checkpoints

This page does not re-own stage semantics. Product kernels, record families,
and stage-owned vocabularies still belong to the existing owner pages such as
[Pipeline Stage Contracts](../concepts/pipeline-stage-contracts.md),
[Domain Ontology](../concepts/domain-ontology.md), and
[Gaps And Readiness](../concepts/gaps-and-readiness.md).

## Canonical Scalar Forms

Use these forms anywhere a target-stage contract refers to canonical emitted
values, stable-id components, or fingerprint inputs.

- `StableIdString` uses the format `<kind>:<sha256(lowercase-hex)>`.
- `DecimalString` uses base-10 string form only:
  - no exponent form
  - no `-0`
  - strip insignificant trailing fractional zeroes
  - keep one leading `0` before a decimal point
  - canonical zero is `0`
- `TimestampString` uses UTC RFC 3339 with `Z`:
  - preserve fractional seconds only when present in the canonical runtime
    value
  - never serialize target-product timestamps with a non-UTC offset
- `DateString` uses `YYYY-MM-DD`.
- `EnumString` uses the exact lowercase token published by the owning
  vocabulary.
- `Null` uses JSON `null`.

These forms are the canonical fingerprint inputs for every target product unless
an owning page publishes one more specific field rule.

## Canonical Tuple And Anchor Rules

Stable-id component arrays and fingerprint anchors may use only:

- stable-id strings
- enum strings
- decimal strings
- canonical date strings
- canonical timestamp strings
- integers
- `null`
- arrays composed only of the same canonical component types

Anchors must never use:

- prose messages
- filesystem paths
- human labels
- unordered objects or maps
- derived counts
- display-only formatting

Slice-specific pages may define exact anchor tuples, but those tuples must stay
within this admissibility rule.

## Shared Dataset Identity

`dataset_id` identifies one persisted target-product dataset.

Rules:

- `dataset_id` uses the format `dataset:<sha256(lowercase-hex)>`
- the component array is `[product_slug, product_fingerprint]`
- `dataset_id` is content-addressed and independent of filesystem location

Frozen `product_slug` vocabulary:

- `evidence-set`
- `claim-set`
- `economic-facts`
- `reconciliation-state`
- `checkpoint`
- `journal`
- `tax-inputs`
- `tax-outputs`

## Claim Compiler Identity

`claim_emitter_id` identifies the shared compiler or translation family that
emitted one `ClaimSet`.

Rules:

- `claim_emitter_id` uses the format `claim-emitter:<sha256(lowercase-hex)>`
- the component array is `[source, adapter_id, emitter_slug]`
- `emitter_slug` must be kebab-case
- the default first-slice `emitter_slug` is `bridge-claim-compiler`

## AssertionValue

`AssertionValue` is the shared value union reused by reconciliation and
checkpoints.

Variants:

- `QuantityValue`
  - `quantity`
  - `subject_ref`
  - `instrument_ref_or_null`
  - `location_ref_or_null`
- `MoneyValue`
  - `amount`
  - `currency`
- `OwnerValue`
  - `legal_owner_ref_or_null`
  - `beneficial_owner_ref_or_null`
  - `counterparty_ref_or_null`
- `LocationValue`
  - `location_ref`

Rules:

- the union remains explicit so later implementation cannot silently collapse
  quantity, money, ownership, and location truth into one scalar convenience
  type
- the canonical value fingerprint uses one stable UTF-8 JSON object keyed by
  variant name plus the canonical variant payload
- `CheckpointAssertionRecord.accepted_value` uses this union
- `BalanceTargetRecord.expected_value` uses this union
- `BalanceTargetRecord.observed_value_or_null` uses this union

## Journal Reference Types

`AccountRef` identifies one accounting account.

Rules:

- `AccountRef` serializes and sorts as `[chart_id, account_code]`

`CommodityRef` identifies one posting commodity.

Rules:

- `CommodityRef` serializes and sorts as `[commodity_kind, commodity_id]`

Frozen `commodity_kind` vocabulary:

- `instrument`
- `currency`
- `synthetic_unit`

`OriginRef` identifies the immediate kernel origin for one posting.

Rules:

- `OriginRef` serializes and sorts as `[origin_kind, origin_id]`
- `origin_kind` identifies the immediate accounting origin, not a human-facing
  provider, source, or renderer label

Frozen `origin_kind` vocabulary:

- `economic_leg`
- `checkpoint_assertion`
- `adjustment_basis`

## Tax Policy Identity

`TaxPolicyId` identifies one selected tax policy.

Rules:

- `TaxPolicyId` uses the format `tax-policy:<sha256(lowercase-hex)>`
- the component array is `[jurisdiction_or_regime, policy_slug, policy_version]`
- `policy_slug` must be kebab-case
- forward-looking target tax-stage docs use `tax_policy_id` for this contract
