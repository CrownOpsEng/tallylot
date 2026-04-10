---
title: "Workspace Model"
summary: "Conceptual overview of the external workspace, seeded files, and mirrored repo guidance."
doc_type: concept
audience: human
owner: repo
status: active
nav_order: 50
---

The application operates against an external workspace rooted outside the repo.
The repo owns the guidance and templates for that workspace, but not the live
evidence or generated operational artifacts.

## Why The Workspace Is External

- raw evidence should not live inside the git checkout
- generated artifacts need deterministic paths across repeated runs
- operators need a stable place for captures, verification exports, and
  checkpoint outputs that is separate from source control

## Top-Level Shape

The workspace is seeded by `workspace init` with these major areas:

- `analysis/` for issue tracking, inventory, and reconciliation packages
- `config/` for workspace configuration state
- `docs/` for live operator copies inside the external workspace
- `evidence/` for raw source and portfolio artifacts
- `outputs/` for checkpoints, logs, and reports
- `working/` for normalized, staged, verification, and supporting artifacts

## Repo Relationship

- repo-side guidance lives under `docs/workspace/`
- `docs/workspace/` intentionally mirrors runtime path names, including
  underscore-preserving names where the runtime uses them
- workspace docs under the external root are live copies, not the versioned
  source of truth

## Seeded Control Files

- `analysis/issues/issue_log.csv`
- `analysis/issues/source_inventory.csv`
- `analysis/inventory/source_captures.csv`
- `analysis/issues/source_label_map.csv`
- `analysis/inventory/location_inventory.csv`
- `outputs/logs/round_log.csv`
- `config/workspace.json`

## Capture And Assembly Model

The workspace model uses explicit capture records and assembled source
datasets.

Rules:

- `source_inventory.csv` is source-summary state only; it does not pretend one
  source has one canonical `capture_path`
- `analysis/inventory/source_captures.csv` is the append-only capture registry
  keyed by immutable `capture_uid`
- one intake run materializes one raw capture root under
  `evidence/raw/source/<source>/<capture_label>/`
- `capture_label` is a human-facing folder name, while `capture_uid` remains
  the canonical capture identity
- inferred periods stay in metadata and reports; they do not control capture
  routing
- untouched upstream originals remain under raw evidence even when they are
  statement PDFs, HTML exports, ZIP archives, extracted archive members, or
  required sidecars
- `working/supporting_artifacts/` is only for derived or operator-authored
  helper material
- capture-scoped normalized outputs live under
  `working/normalized/captures/<capture_uid>/`
- source-scoped assembled datasets live under
  `working/normalized/sources/<source>/`
- reconciliation consumes assembled source datasets rather than crawling raw
  capture layouts directly

## Read Next

- `docs/workspace/README.md`
- `docs/workspace/working/README.md`
- `docs/workspace/analysis/issues/README.md`
- `docs/workspace/outputs/checkpoints/README.md`
