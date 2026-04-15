---
title: "Target Contract Primitives"
summary: "Helper reference for reusable ids and tuples that complement the owner pages without redefining target product contracts."
doc_type: reference
audience: human
owner: repo
status: active
nav_order: 17
related:
  - docs/concepts/pipeline-stage-contracts.md
  - docs/concepts/domain-ontology.md
  - docs/concepts/gaps-and-readiness.md
  - ROADMAP.md
---

Use this page as a helper reference when a target-stage implementation needs a
reusable id helper or tuple that is not itself a stage contract. Owner pages
take precedence.

## Precedence

Use the owner pages first:

- [Pipeline Stage Contracts](../concepts/pipeline-stage-contracts.md) for
  stable-id format, target product ids, upstream product refs, target product
  kernels, and shared status vocabularies
- [Domain Ontology](../concepts/domain-ontology.md) for `AssertionValue`,
  `PositionRef`, `ContractRef`, `BasisPoolRef`, and other domain ref seams
- [Gaps And Readiness](../concepts/gaps-and-readiness.md) for `SubjectRef`,
  shared support attachments, and `dataset_id`

This page keeps only reusable helper ids and tuples that are not primary owner
concepts elsewhere.

## Claim Producer Identity

`claim_producer_id` identifies the shared compiler or translation family that
produced one `ClaimSet`.

Rules:

- `claim_producer_id` uses the stable-id format owned by
  [Pipeline Stage Contracts](../concepts/pipeline-stage-contracts.md)
- the component array is `[source, adapter_id, producer_slug]`
- `producer_slug` must be kebab-case
- the default first-slice `producer_slug` is `claim-compiler`

## Valuation Source Identity

`ValuationSourceRef` identifies the immediate source that justified one
`ValuationRecord`.

Rules:

- `ValuationSourceRef` serializes and sorts as `[source_kind, source_id]`
- `source_kind` names the immediate valuation source surface, such as
  `claim`, `evidence_observation`, or `market_reference`
- when the source is already a target-kernel subject, `source_id` uses that
  subject's stable id
- when the source is an external market reference, `source_id` uses the
  stage-owned stable market anchor rather than renderer-local prose

## Accounting Reference Tuples

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
- `origin_kind` identifies the immediate accounting origin, not a provider or
  renderer label
- `PostingRecord.origin_ref` uses `OriginRef`

Frozen `origin_kind` vocabulary:

- `economic_leg`
- `checkpoint_assertion`
- `adjustment_basis`

## Tax Policy Identity

`TaxPolicyId` identifies one selected tax policy.

Rules:

- `TaxPolicyId` uses the stable-id format owned by
  [Pipeline Stage Contracts](../concepts/pipeline-stage-contracts.md)
- the component array is `[jurisdiction_or_regime, policy_slug, policy_version]`
- `policy_slug` must be kebab-case

## Reminder

Do not implement target product ids, upstream product refs, `dataset_id`,
`AssertionValue`, `SubjectRef`, or target product kernel structure from this
page. Those contracts live on their owner pages.
