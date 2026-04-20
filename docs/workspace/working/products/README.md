---
title: "Product Outputs"
summary: "Reference for authoritative target-product kernels and product-local compatibility views under working/products/."
doc_type: reference
audience: both
owner: repo
status: active
naming_scope: workspace_reference
---

Use this subtree for authoritative target-product kernels and any product-local
compatibility views that are derived from those kernels.

Current runtime surface:

- `working/products/evidence_sets/<evidence_set_id>/evidence_set.json` is the
  authoritative `EvidenceSet` kernel for the bounded evidence-selection and
  typed statement-observation scope in planner-enabled Coinbase normalization
- `working/products/evidence_sets/<evidence_set_id>/compatibility/translation_input_plan.json`
  is the legacy planning view derived from that kernel
- `working/products/claim_sets/<claim_set_id>/claim_set.json` is the
  authoritative `ClaimSet` kernel for the bounded Coinbase evidence-local
  meaning slice
- `working/products/claim_sets/<claim_set_id>/assessment/gap/` and
  `assessment/review/` store deterministic claim-stage gap and review sidecars,
  even when those arrays are empty
- `working/products/claim_sets/<claim_set_id>/compatibility/draft_projection_fields.json`
  stores the retained bridge-only draft projection fields used to rebuild
  `EconomicActivityDraft` and `SourceTranslationBatch`
- `working/products/economic_facts/<economic_facts_id>/economic_facts.json`
  is the authoritative `EconomicFacts` kernel for the bounded downstream
  Coinbase slice, with `compatibility/facts.csv` and
  `compatibility/fact_annotations.json` derived from that kernel
- `working/products/reconciliation_states/<reconciliation_state_id>/reconciliation_state.json`
  is the authoritative `ReconciliationState` kernel for one bounded continuity
  segment in that slice, with `compatibility/balance_snapshots.csv` derived
  from that kernel
- `working/products/checkpoints/<checkpoint_id>/checkpoint.json` is the
  authoritative `Checkpoint` kernel for one accepted as-of point in that
  slice, with `compatibility/balance_references.csv` derived from that kernel

The normalized capture output under `working/normalized/captures/<capture_uid>/`
may still mirror retained compatibility files for current readers, but the
authoritative kernel lives here when a product is authoritative. For the
bounded planner-enabled Coinbase slice, `EconomicFacts`,
`ReconciliationState`, and `Checkpoint` now live here as the authoritative
downstream product directories, while current readers may still consume
capture-scoped compatibility files derived from those kernels.

Target-direction planning note:

- when `Journal` lands, the journal kernel and backend-neutral detail are
  expected under `working/products/journals/<journal_id>/`
- the first backend-specific journal artifacts are expected under
  `working/products/journals/<journal_id>/backends/ledger_cli/`
- those journal paths are not part of the current runtime surface today
