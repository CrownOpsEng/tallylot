---
title: "Source Raw Exports"
summary: "Rules for untouched upstream source evidence stored under the mirrored workspace source tree."
doc_type: reference
audience: both
owner: repo
status: active
---

Store untouched external source evidence here. This branch is only for exchange, wallet, explorer, bot, and other upstream-system exports.

Rules:

- never overwrite raw files
- keep original filenames when practical
- keep each capture in its own capture folder when routing new intake
- write `manifest.csv` inside the capture folder, not at the source root
- do not place CoinTracking exports here; those belong under `evidence/raw/portfolio/`

Preferred structure for new intake:

- `evidence/raw/source/<source>/<capture_id>/`
- `evidence/raw/source/<source>/<capture_id>/manifest.csv`

`<source>` is an operator-managed stable label, not an adapter contract. Use a
name that is consistent and meaningful in the workspace, but do not rename a
capture folder just to satisfy one adapter. Adapter resolution should come from
file families and content signatures first, with source labels used only as
low-confidence hints when content is insufficient.

Bundle-aware intake may create nested bundle paths inside a capture, for example:

- `evidence/raw/source/<source>/<capture_id>/<bundle_id>/archive/...`
- `evidence/raw/source/<source>/<capture_id>/<bundle_id>/contents/...`

Some older tracked captures still use pre-refactor subpaths such as `raw/`. Keep those files immutable, but do not copy that layout into new intake work.
