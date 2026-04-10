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
- `balances.csv`
- `balance_evidence.csv`
- `balance_confirmations.csv`
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
- `balances.csv`
- `balance_evidence.csv`
- `balance_confirmations.csv`
- `exceptions.csv`
- `normalization_reviews.csv`
- `location_inventory.csv`
- `assembly_summary.json`
- `assembly_issues.csv`

Reconciliation reads only assembled source datasets from
`working/normalized/sources/`.

`fact_annotations.json` preserves fact-keyed provenance references and
review markers that originate on drafts.

`facts.csv` is schema-versioned and stores canonical signed legs keyed by
`instrument_id`.

`balances.csv` contains application-derived balances from transaction facts and
persists `instrument_id`, `as_of_at`, and `as_of_precision`.

`balance_evidence.csv` contains source-backed checkpoint evidence when the
adapter actually provides it, using the same `instrument_id` and temporal
precision fields as `balances.csv`.

Each `balance_evidence.csv` row flattens the shared provenance locator columns:

- `capture_uid`
- `relative_path`
- `archive_member_path`
- `locator_kind`
- `anchor`

`balance_confirmations.csv` contains accepted operator confirmations written by
checkpoint-owned manual balance submission. It is a lower-trust runtime
reference surface than `balance_evidence.csv` and does not satisfy filing-ready
checkpoint evidence requirements on its own.

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
