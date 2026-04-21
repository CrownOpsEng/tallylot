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
  - docs/reference/evidence-claim-contract.md
  - docs/reference/economics-reconciliation-checkpoint-contract.md
  - docs/reference/journal-contract.md
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
- [Evidence And Claim Contract](evidence-claim-contract.md) and
  [Economics Reconciliation Checkpoint Contract](economics-reconciliation-checkpoint-contract.md) plus
  [Journal Contract](journal-contract.md) for bounded-contract persistence,
  compatibility, backend, and validation expectations

## Persistence Rules

**Exception rationale:** `assessment/` stays in this page only as the shared
persistence root for the nested `gap/` and `review/` sidecar families. It is
not a generic sidecar bucket.

When persisting target products:

- classify persisted content as one of:
  - authoritative kernels
  - product-local detail
  - backend-specific derived accounting artifacts
  - future semantic read models
- persist one authoritative kernel per declared partition scope
- keep authoritative kernels under product-owned directories rather than
  migration-era source or checkpoint containers
- keep product ids in the product header and keep those product ids distinct from
  `kernel_scope_id`
- keep partition-scope labels aligned to the contract pages' stage-owned scope
  names instead of inventing alternate helper vocabulary here
- keep product-local detail beside the authoritative kernel with explicit
  owning-product basenames, for example
  `working/products/journals/<journal_id>/journal_entry_check_reports.json`
- keep bridge CSVs and bridge draft or batch surfaces as compatibility
  views only once a target product is authoritative for that scope
- keep backend-specific generated artifacts under an immediate backend-id split,
  for example
  `working/products/journals/<journal_id>/backends/ledger_cli/validation_findings.json`
- keep provenance, explanations, reviews, comparison traces, and other
  non-kernel detail in sidecars
- backend-specific generated artifacts are non-authoritative detail, not
  compatibility views, tax inputs, or product identity inputs
- backend-generated artifacts are never authoritative storage and never the
  primary cross-capability query API
- keep grouped readiness as tax-output-local, narrow rendering-local, or
  compatibility-local derived output until the roadmap trigger ladder
  activates a capability-owned read-model surface
- keep assessment family directories and basenames aligned to the stored
  families, for example `assessment/gap/gap_records.json`,
  `assessment/review/review_records.json`
- `assessment/` stays generic only because it splits immediately into the
  persisted `gap/` and `review/` families; unrelated sidecars do not belong
  there
- `backends/` stays allowed only because it splits immediately into backend-id
  families; it is not a generic mixed-detail bucket
- keep product-local derived outputs under `derived/` inside the owning
  product directory when a contract explicitly allows them, for example
  `working/products/tax_outputs/<tax_outputs_id>/derived/tax_output_grouped_readiness.json`
- defer a general projections root such as
  `working/projections/<capability>/<projection_family>/...` until a later
  capability-specific increment activates broader derived read models
- treat shared assessment outputs as declared persisted outputs
- treat caches and indexes as regenerable accelerators, not as business truth

## Reminder

Do not implement target persistence from this page alone. The authoritative
placement, product-id, and storage rules live on the contract pages listed
above.
