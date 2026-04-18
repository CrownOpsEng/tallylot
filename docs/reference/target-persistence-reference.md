---
title: "Target Persistence Reference"
summary: "Target persistence, partition-scope, and compatibility placement reference."
doc_type: reference
audience: human
owner: repo
status: active
naming_scope: forward_target
nav_order: 18
related:
  - docs/concepts/pipeline-stage-contracts.md
  - docs/concepts/reconciliation-tax-architecture.md
  - docs/reference/first-upstream-slice-contract.md
  - docs/reference/first-downstream-slice-contract.md
  - ROADMAP.md
---

Use this page when you need target persistence guidance. It does not define a
second persistence contract.

## Precedence

Use these contract pages first:

- [Pipeline Stage Contracts](../concepts/pipeline-stage-contracts.md) for
  target product kernels, record families, ids, and fingerprints
- [Reconciliation, Checkpoint, Journal, And Tax Architecture](../concepts/reconciliation-tax-architecture.md)
  for persistence model, partition scopes, default filesystem placement,
  sidecars, replace rules, caches, and indexes
- [First Upstream Slice Contract](first-upstream-slice-contract.md) and
  [First Downstream Slice Contract](first-downstream-slice-contract.md) for
  bounded-slice persistence and compatibility expectations

## Persistence Rules

**Exception rationale:** `assessment/` stays in this page only as the shared
persistence root for the nested `gap/`, `review/`, and `readiness/` sidecar
families. It is not a generic sidecar bucket.

When persisting target products:

- persist one authoritative kernel per declared partition scope
- keep authoritative kernels under product-owned directories rather than
  migration-era source or checkpoint containers
- keep product ids in the product header and keep those product ids distinct from
  `kernel_scope_id`
- keep partition-scope labels aligned to the contract pages' stage-owned scope
  names instead of inventing alternate helper vocabulary here
- keep bridge CSVs and bridge draft or batch surfaces as compatibility
  views only once a target product is authoritative for that scope
- keep provenance, explanations, reviews, comparison traces, and other
  non-kernel detail in sidecars
- keep grouped readiness and other source-grouped views as assessment views or
  compatibility views rather than as canonical shared record families
- keep assessment family directories and basenames aligned to the stored
  families, for example `assessment/gap/gap_records.json`,
  `assessment/review/review_records.json`,
  and `assessment/readiness/readiness_records.json`
- `assessment/` stays generic only because it splits immediately into the
  persisted `gap/`, `review/`, and `readiness/` families; unrelated sidecars
  do not belong there
- defer a general projections root such as
  `working/projections/<slice>/<projection_family>/...` until the roadmap
  trigger ladder activates broader derived read models
- treat caches and indexes as regenerable accelerators, not as business truth

## Reminder

Do not implement target persistence from this page alone. The authoritative
placement, product-id, and storage rules live on the contract pages listed
above.
