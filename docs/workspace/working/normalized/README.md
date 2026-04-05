---
title: "Normalized Files"
summary: "Artifact contract for deterministic per-source normalized outputs and working candidates."
doc_type: reference
audience: both
owner: repo
status: active
---

Place deterministic normalized source artifacts here after profiling and field normalization.

Do not treat files here as raw evidence. The raw source must remain in `evidence/raw/source/`.

Per-source folders should use the typed pipeline artifact set:

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

`fact_annotations.json` preserves fact-keyed provenance references and
review markers that originate on drafts.

`facts.csv` is schema-versioned and stores canonical signed legs keyed by
`instrument_id`.

`balances.csv` contains application-derived balances from transaction facts and
persists `instrument_id`, `as_of_at`, and `as_of_precision`.

`balance_evidence.csv` contains source-backed checkpoint evidence when the
adapter actually provides it, using the same `instrument_id` and temporal
precision fields as `balances.csv`.

`balance_confirmations.csv` contains accepted operator confirmations written by
checkpoint-owned manual balance submission. It is a lower-trust runtime
reference surface than `balance_evidence.csv` and does not satisfy filing-ready
checkpoint evidence requirements on its own.

`cointracking_candidate.csv` is optional. Create it with `output render file`
when the round needs it, and keep it beside the
normalized artifacts only as a working file. Only
`working/import_batches/` should hold files that have passed overlap
screening and are approved for import.

`profile_inventory.csv` includes timezone provenance columns so agents and users
can inspect timestamp semantics without reopening raw files.

`timezone_issues.csv` holds blocking provenance conflicts. Non-blocking
assumptions are recorded in `normalization_reviews.csv`.
