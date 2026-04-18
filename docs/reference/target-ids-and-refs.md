---
title: "Target Ids And Refs"
summary: "Reusable target ids and ref tuples that are shared across target contracts."
doc_type: reference
audience: human
owner: repo
status: active
naming_scope: forward_target
nav_order: 17
related:
  - docs/concepts/pipeline-stage-contracts.md
  - docs/concepts/domain-ontology.md
  - docs/concepts/gaps-and-reviews.md
  - ROADMAP.md
---

Use this page when a target-stage implementation needs a reusable target id or
ref tuple that is not itself a stage contract. The detailed contract pages take
precedence.

**Locality rule:** This page restates `source_slug` and `market_input` only
where reusable ids or ref tuples still need evidence-local or origin-local
compatibility language. Those terms stay local to those seams and do not become
broader target vocabulary.

## Precedence

Use the detailed contract pages first:

- [Pipeline Stage Contracts](../concepts/pipeline-stage-contracts.md) for
  stable-id format, target product ids, upstream product refs, target product
  kernels, and shared status vocabularies
- [Domain Ontology](../concepts/domain-ontology.md) for `AssertionValue`,
  `PositionRef`, `ContractRef`, `BasisPoolRef`, and other domain refs plus
  identity seams
- [Gap, Review, And Shared Attachment](../concepts/gaps-and-reviews.md) for
  `SubjectRef`, shared gap/review attachments, and `kernel_scope_id`

This page keeps only reusable target ids and ref tuples that are not defined as
the primary contract content elsewhere.

## Identifier Namespaces

This page documents canonical reusable ids and refs only.

- local id slots are not reusable id families
- owner-local slot forms belong only on the matching contract pages and slice mirrors where
  the catalog explicitly allows them
- if a canonical id is already short, it has no paired local alias unless the
  catalog declares one

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
- when the origin is an external market input, `origin_id` uses the
  stage-owned stable market key rather than renderer-local prose

Frozen `origin_kind` vocabulary:

- `claim`
- `evidence_observation`
- `market_input`
- `economic_leg`
- `checkpoint_assertion`
- `basis_adjustment`

`OriginRef.origin_kind = market_input` stays on the origin axis. It names an
immediate upstream source class, not a valuation-purpose member.

## Journal Refs

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

Do not implement target product ids, upstream product refs, `kernel_scope_id`,
`AssertionValue`, `SubjectRef`, or target product kernel structure from this
page. Those contracts live on their primary contract pages.
