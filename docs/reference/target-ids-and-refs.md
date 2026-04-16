---
title: "Target Ids And Refs"
summary: "Helper reference for reusable target ids and ref tuples that complement the owner pages without redefining product contracts."
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
reusable target id or ref tuple that is not itself a stage contract. Owner
pages take precedence.

## Precedence

Use the owner pages first:

- [Pipeline Stage Contracts](../concepts/pipeline-stage-contracts.md) for
  stable-id format, target product ids, upstream product refs, target product
  kernels, and shared status vocabularies
- [Domain Ontology](../concepts/domain-ontology.md) for `AssertionValue`,
  `PositionRef`, `ContractRef`, `BasisPoolRef`, and other domain refs plus
  identity seams
- [Gaps And Readiness](../concepts/gaps-and-readiness.md) for `SubjectRef`,
  shared gap/review/readiness attachments, and `product_scope_id`

This page keeps only reusable target ids and ref tuples that are not primary
owner concepts elsewhere.

## Emitter Id

`emitter_id` identifies the shared claim emitter that emitted one `ClaimSet`.

Rules:

- `ClaimSet.emitter_id` uses the stable-id format owned by
  [Pipeline Stage Contracts](../concepts/pipeline-stage-contracts.md)
- the component array is `[source_slug, adapter_id, emitter_key]`
- `source_slug` stays the same across evidence-local products
- `emitter_id` is evidence-local only; later products keep lineage through
  `claim_set_ref` or `claim_set_refs` rather than carrying `source_slug`,
  `adapter_id`, or `emitter_id` forward
- `emitter_key` must be kebab-case
- the first upstream slice `emitter_key` is `claim`

## Origin Ref

`OriginRef` identifies the immediate upstream origin for one emitted kernel
record.

Rules:

- `ValuationRecord.origin_ref` and `PostingRecord.origin_ref` use `OriginRef`
- `OriginRef` serializes and sorts as `[origin_kind, origin_id]`
- `origin_kind` names the immediate upstream origin, not a source-system or
  renderer label
- when the origin is already a target-product record or subject, `origin_id`
  uses that stable id
- when the origin is an external market reference, `origin_id` uses the
  stage-owned stable market key rather than renderer-local prose

Frozen `origin_kind` vocabulary:

- `claim`
- `evidence_observation`
- `market_reference`
- `economic_leg`
- `checkpoint_assertion`
- `basis_adjustment`

## Journal Helper Refs

`JournalAccountRef` identifies one chart account.

Rules:

- `PostingRecord.account_ref` uses `JournalAccountRef`
- `JournalAccountRef` serializes and sorts as `[chart_id, account_code]`

`JournalUnitRef` identifies one journal unit.

Rules:

- `PostingRecord.unit_ref` uses `JournalUnitRef`
- `JournalUnitRef` serializes and sorts as `[unit_kind, unit_id]`

Frozen `unit_kind` vocabulary:

- `instrument`
- `currency`
- `synthetic_unit`

## Tax Policy Id

`TaxPolicyId` identifies one selected tax policy.

Rules:

- `TaxPolicyId` uses the stable-id format owned by
  [Pipeline Stage Contracts](../concepts/pipeline-stage-contracts.md)
- the component array is `[jurisdiction_or_regime, policy_key, policy_version]`
- `policy_key` must be kebab-case

## Reminder

Do not implement target product ids, upstream product refs, `product_scope_id`,
`AssertionValue`, `SubjectRef`, or target product kernel structure from this
page. Those contracts live on their owner pages.
