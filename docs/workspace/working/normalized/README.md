---
title: "Normalized Files"
summary: "Artifact contract for capture-scoped normalization outputs, assembled source datasets, and working candidates."
doc_type: reference
audience: both
owner: repo
status: active
---

Place deterministic normalized artifacts here after profiling, field
normalization, and source assembly.

Do not treat files here as raw evidence. The raw source must remain in `evidence/raw/source/`.

## Capture Outputs

Capture-scoped normalized roots live under:

- `working/normalized/captures/<capture_uid>/`

These folders hold the typed pipeline artifact set for one capture:

- `profile.json`
- `profile_inventory.csv`
- `timezone_issues.csv`
- `facts.csv`
- `fact_annotations.json`
- `balance_snapshots.csv`
- `balance_references.csv`
- `balance_reference_issues.csv`
- `exceptions.csv`
- `normalization_reviews.csv`
- `location_inventory.csv`
- `normalization_summary.json`

## Assembled Source Outputs

Source assembly writes the reconciliation-ready dataset under:

- `working/normalized/sources/<source>/`

These folders keep the familiar per-source artifact surface, plus assembly
artifacts:

- `facts.csv`
- `fact_annotations.json`
- `balance_snapshots.csv`
- `balance_references.csv`
- `balance_reference_issues.csv`
- `exceptions.csv`
- `normalization_reviews.csv`
- `location_inventory.csv`
- `assembly_summary.json`
- `assembly_issues.csv`

Reconciliation reads only assembled source datasets from
`working/normalized/sources/`.

`fact_annotations.json` preserves fact-keyed provenance references and
review markers that originate on drafts.

`facts.csv` is schema-versioned and stores signed transaction legs keyed by
`instrument_id`.

`balance_snapshots.csv` contains application-derived balances from transaction
facts and persists `instrument_id`, `target_at`, and `target_precision`.

`balance_references.csv` contains the unified balance reference surface.
Normalization contributes `source_document` rows when the adapter actually
provides document-backed balance evidence. Later workflows may add
`network_api` or `operator_assertion` rows for the same target model.

`balance_reference_issues.csv` stores explicit unresolved or unsupported
reference issues emitted during normalization, assembly, or later hydration.

`cointracking_candidate.csv` is optional. Create it with `output render file`
when the round needs it, and keep it beside the
assembled source artifacts only as a working file. Only
`working/import_batches/` should hold files that have passed overlap
screening and are approved for import.

`profile_inventory.csv` is the capture-scoped discovery contract for downstream
normalization. In addition to timezone provenance, it records fields such as
`capture_uid`, `source`, `evidence_role`, `observed_period_start`,
`observed_period_end`, `observed_period_label`, `statement_kind`, and
`originality_class` so statement extraction and issue-context resolution do not
need to rediscover raw files by crawling the tree.

`balance_references.csv` preserves the flattened source-document provenance
locator columns directly:

- `capture_uid`
- `relative_path`
- `archive_member_path`
- `locator_kind`
- `anchor`

`exceptions.csv` and `normalization_reviews.csv` preserve `raw_row_ref` and the
same flattened locator family with `raw_` prefixes:

- `raw_capture_uid`
- `raw_relative_path`
- `raw_archive_member_path`
- `raw_locator_kind`
- `raw_anchor`

`timezone_issues.csv` holds blocking provenance conflicts. Non-blocking
assumptions are recorded in `normalization_reviews.csv`.

`source assemble` owns the generated source dataset under
`working/normalized/sources/<source>/`. Reruns rewrite only the known generated
artifacts in that folder and preserve unrelated operator-owned files beside
them.
