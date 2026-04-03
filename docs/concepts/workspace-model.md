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
- `analysis/inventory/location_inventory.csv`
- `outputs/logs/round_log.csv`
- `config/workspace.json`

## Read Next

- `docs/workspace/README.md`
- `docs/workspace/working/README.md`
- `docs/workspace/analysis/issues/README.md`
- `docs/workspace/outputs/checkpoints/README.md`
