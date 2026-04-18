---
title: "Target Product Artifacts"
summary: "Helper reference that points to the owner pages for target persistence, partitions, and bounded slice artifact expectations."
doc_type: reference
audience: human
owner: repo
status: active
nav_order: 18
related:
  - docs/concepts/pipeline-stage-contracts.md
  - docs/concepts/reconciliation-tax-architecture.md
  - docs/reference/first-slice-contract.md
  - docs/reference/first-downstream-slice-contract.md
  - ROADMAP.md
---

Use this page as a routing reference when you need target artifact guidance.
It does not define a second artifact contract.

## Precedence

Use these pages as the authoritative sources:

- [Pipeline Stage Contracts](../concepts/pipeline-stage-contracts.md) for
  target product kernels, record families, ids, and fingerprints
- [Reconciliation And Tax Architecture](../concepts/reconciliation-tax-architecture.md)
  for persistence model, partition scopes, default filesystem placement,
  sidecars, replace semantics, caches, and indexes
- [First Slice Contract](first-slice-contract.md) and
  [First Downstream Slice Contract](first-downstream-slice-contract.md) for
  bounded-slice artifact and compatibility expectations

## Artifact Rules

When persisting target products:

- persist one authoritative kernel per declared scope partition
- keep product ids in kernel metadata and keep those product ids distinct from
  `dataset_id`
- keep bridge CSVs and bridge bundles as compatibility projections only once a
  target product is authoritative for that scope
- keep provenance, explanations, reviews, comparison traces, and other
  non-kernel detail in sidecars
- treat caches and indexes as regenerable accelerators, not as business truth

## Reminder

Do not implement target persistence from this page alone. The authoritative
placement, product-id, and storage rules live on the owner pages listed above.
