---
title: "Workspace Reference"
summary: "Mirrored repo reference for the external workspace layout, templates, and subtree contracts."
doc_type: reference
audience: both
owner: repo
status: active
---

This subtree holds repo-owned guidance and templates for the external
workspace. Keep live evidence and operator outputs in the workspace itself, but
keep the guidance that explains those paths versioned here.

Use [`docs/concepts/workspace-model.md`](../concepts/workspace-model.md) for
the overall workspace shape and seeded files. Use this subtree when you need
rules for one specific workspace area.

This subtree intentionally mirrors the runtime workspace shape. Unlike the
top-level docs, some directory names here keep underscores because the runtime
paths keep them too.

## Scope

- This subtree owns repo-side guidance and templates for workspace paths.
- It does not own the live contents of the external workspace.
- It does not replace the higher-level runtime and workflow docs under
  `docs/guides/` and `docs/reference/`.

## Evidence

- [`evidence/raw/source/README.md`](evidence/raw/source/README.md): raw source
  evidence conventions
- [`evidence/raw/portfolio/README.md`](evidence/raw/portfolio/README.md):
  portfolio export bundle conventions

## Working

- [`working/README.md`](working/README.md): derived working-file boundaries
- [`working/import_batches/README.md`](working/import_batches/README.md): staged
  import batch rules
- [`working/normalized/README.md`](working/normalized/README.md): normalized
  output guide
- [`working/supporting_artifacts/README.md`](working/supporting_artifacts/README.md):
  non-raw derivative guidance
- [`working/supporting_artifacts/balance_submissions/README.md`](working/supporting_artifacts/balance_submissions/README.md):
  manual balance submission package guidance
- [`working/verification/README.md`](working/verification/README.md):
  verification export structure

## Analysis

- [`analysis/checklists/work-checklists.md`](analysis/checklists/work-checklists.md):
  repair and import round checklists
- [`analysis/inventory/README.md`](analysis/inventory/README.md): location
  inventory output guide
- [`analysis/issues/README.md`](analysis/issues/README.md): issue and source
  inventory file guide
- [`analysis/reconciliation/README.md`](analysis/reconciliation/README.md):
  reconciliation output guide

## Templates

- [`analysis/issues/issue-log-template.csv`](analysis/issues/issue-log-template.csv):
  issue log seed example
- [`analysis/issues/source-inventory-template.csv`](analysis/issues/source-inventory-template.csv):
  source inventory seed example
- [`analysis/issues/source-label-map-template.csv`](analysis/issues/source-label-map-template.csv):
  stable source-label map seed example
- [`analysis/reconciliation/reconciliation-template.csv`](analysis/reconciliation/reconciliation-template.csv):
  reconciliation seed example

## Outputs

- [`outputs/checkpoints/README.md`](outputs/checkpoints/README.md): checkpoint
  output guidance
- [`outputs/checkpoints/2025-12-31-final/README.md`](outputs/checkpoints/2025-12-31-final/README.md):
  expected 2025 year-end checkpoint target
- [`outputs/reports/README.md`](outputs/reports/README.md): closeout report
  guidance
