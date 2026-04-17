---
title: "Working Files"
summary: "Reference for derived working files used during normalization, staging, and verification."
doc_type: reference
audience: both
owner: repo
status: active
naming_scope: workspace_reference
---

This tree holds derived files used to prepare import batches and verify
round-close changes.

Some verification folders may contain exports from a concrete external
verification tool. That is a workflow detail, not the definition of the tree
itself.

Subfolders:

- `supporting_artifacts/` for non-raw derivatives discovered during intake,
  such as calc sheets, draft import workbooks, screenshots, rendered HTML
  saves, and manual balance submission packages
- `normalized/` for cleaned but not yet approved source files
- `import_batches/` for reviewed import candidates
- `verification/` for fresh verification export sets captured after each repair
  or import round

Nothing here is a raw source of truth.

Some working paths remain source-scoped even though they are not raw evidence.
When intake needs manual control over those source associations, use
`analysis/issues/source_label_map.csv` so the derived artifacts land under the
same stable operator-managed source label as the related raw capture.
