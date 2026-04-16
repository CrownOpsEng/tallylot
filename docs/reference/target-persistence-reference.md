---
title: "Target Persistence Reference"
summary: "Helper reference that points to the owner pages for target persistence, partition scopes, and bounded-slice compatibility expectations."
doc_type: reference
audience: human
owner: repo
status: active
nav_order: 18
related:
  - docs/concepts/pipeline-stage-contracts.md
  - docs/concepts/reconciliation-tax-architecture.md
  - docs/reference/first-upstream-slice-contract.md
  - docs/reference/first-downstream-slice-contract.md
  - ROADMAP.md
---

Use this page as a helper reference when you need target persistence
guidance. It does not define a second persistence contract.

## Precedence

Use these pages as the authoritative owners:

- [Pipeline Stage Contracts](../concepts/pipeline-stage-contracts.md) for
  target product kernels, record families, ids, and fingerprints
- [Reconciliation And Tax Architecture](../concepts/reconciliation-tax-architecture.md)
  for persistence model, partition scopes, default filesystem placement,
  sidecars, replace rules, caches, and indexes
- [First Upstream Slice Contract](first-upstream-slice-contract.md) and
  [First Downstream Slice Contract](first-downstream-slice-contract.md) for
  bounded-slice persistence and compatibility expectations

## Persistence Rules

When persisting target products:

- persist one authoritative kernel per declared partition scope
- keep authoritative kernels under product-owned directories rather than
  migration-era source or checkpoint containers
- keep product ids in the product header and keep those product ids distinct from
  `product_scope_id`
- keep partition-scope labels aligned to the owner pages' stage-owned scope
  names instead of inventing alternate helper vocabulary here
- keep bridge CSVs and bridge draft or batch surfaces as compatibility
  views only once a target product is authoritative for that scope
- keep provenance, explanations, reviews, comparison traces, and other
  non-kernel detail in sidecars
- keep source-grouped views as operator views or compatibility
  views rather than as canonical readiness rollups
- keep support family directories and basenames aligned to the stored
  families, for example `support/gap/gap_records.json`,
  `support/review/review_records.json`,
  `support/readiness/readiness_records.json`, and
  `support/readiness/readiness_rollup_records.json`
- treat caches and indexes as regenerable accelerators, not as business truth

## Reminder

Do not implement target persistence from this page alone. The authoritative
placement, product-id, and storage rules live on the owner pages listed above.
