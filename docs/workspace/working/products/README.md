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

Current implemented runtime surface:

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

The normalized capture output under `working/normalized/captures/<capture_uid>/`
may still mirror retained compatibility files for current readers, but the
authoritative kernel lives here once a product has landed.
