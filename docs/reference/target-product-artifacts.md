---
title: "Target Product Artifacts"
summary: "Forward-looking dataset packaging, kernel filenames, and persistence layout for target pipeline products."
doc_type: reference
audience: human
owner: repo
status: active
nav_order: 18
related:
  - docs/reference/target-contract-primitives.md
  - docs/concepts/pipeline-stage-contracts.md
  - docs/concepts/workspace-model.md
  - docs/status/migration-sequence.md
  - ROADMAP.md
---

Use this page when a forward-looking target product needs a persisted dataset
layout, kernel filename, or sidecar location. This page owns the target product
artifact contract only.

## Purpose And Current-State Note

This page defines the target product artifact contract for forward-looking
pipeline datasets.

Rules:

- this page does not claim these datasets are already live runtime truth
- current bridge artifacts remain under `working/normalized/...` until later
  implementation slices replace them
- target product identity comes from ids and fingerprints, not from artifact
  paths

## Default Workspace Root

The forward-looking default target dataset root is:

- `working/pipeline/<product-slug>/<dataset_id>/`

Rules:

- the path is not part of dataset identity
- interfaces and application services may still support explicit output roots
- dataset identity always comes from stable ids and fingerprints, not from a
  chosen output directory

## Dataset Directory Layout

Every persisted target dataset uses this layout:

- `dataset.json`
- `kernel/`
- `envelopes/`
- `sidecars/`

Rules:

- only `kernel/` participates in product fingerprints unless an owning page says
  otherwise
- `envelopes/` and `sidecars/` are referenceable but excluded from kernel
  fingerprints by default
- kernel records are the replay and reducer authority; envelopes and sidecars
  add explanation, provenance, and stage-local comparison detail

## `dataset.json` Contract

Required fields:

- `product`
- `product_slug`
- `dataset_id`
- `schema_version`
- `product_fingerprint`
- `upstream_dataset_ids`
- `generated_at`
- `kernel_files`
- `envelope_files`
- `sidecar_files`

Optional fields:

- `product_metadata`

Rules:

- `product_metadata` is only for product-scoped inputs used in id recipes but
  not repeated in every row
- the initial allowed example is `ClaimSet` storing `claim_emitter_id` in
  `product_metadata`

## Kernel File Naming

Freeze these kernel filenames:

- `EvidenceSet`
  - `kernel/evidence-records.json`
- `ClaimSet`
  - `kernel/claim-records.json`
  - `kernel/compilation-decision-records.json`
- `EconomicFacts`
  - `kernel/economic-event-records.json`
  - `kernel/economic-leg-records.json`
  - `kernel/valuation-records.json`
- `ReconciliationState`
  - `kernel/continuity-segment-records.json`
  - `kernel/link-records.json`
  - `kernel/balance-target-records.json`
  - `kernel/checkpoint-candidate-records.json`
- `Checkpoint`
  - `kernel/checkpoint-records.json`
  - `kernel/checkpoint-assertion-records.json`
- `Journal`
  - `kernel/journal-entry-records.json`
  - `kernel/posting-records.json`
  - `kernel/validation-records.json`
- `TaxInputs`
  - `kernel/tax-determinant-records.json`
  - `kernel/basis-transition-records.json`
- `TaxOutputs`
  - `kernel/tax-output-records.json`
  - `kernel/carry-forward-records.json`
  - `kernel/unsupported-item-records.json`

## Sidecar And Envelope Rules

Freeze these shared sidecar filenames:

- `sidecars/gaps.json`
- `sidecars/readiness.json`
- `sidecars/reviews.json`

Rules:

- `reviews.json` is stage-local payload, not a shared cross-stage kernel
- richer provenance, explanations, and comparison detail live under
  `envelopes/` keyed by stable ids
- sidecars may be added only when they do not replace kernel business meaning

## Immutability And Discovery

Rules:

- dataset directories are immutable once written because `dataset_id` is
  content-addressed
- “latest” pointers, working indexes, and workflow discovery helpers are
  interface or application concerns, not product-contract fields
- downstream stages consume upstream dataset ids and record ids, not filesystem
  walks over sibling directories
