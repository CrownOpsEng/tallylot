---
title: "Source Intake"
summary: "Detailed procedure for planning, applying, manifesting, and profiling a settled source capture."
doc_type: guide
audience: human
owner: repo
status: active
nav_order: 20
---

Use this guide when you need the detailed typed intake procedure for one source
capture.

## Start From A Settled Capture

1. Treat one intake run as one capture for one source.
2. Start from an untouched incoming dump when the capture is not already in the
   workspace.
3. Keep settled raw files under
   `evidence/raw/source/<source>/<capture_label>/`.
4. Keep inferred periods as metadata only. Do not rename or regroup a capture
   folder around an inferred month or year.
5. Keep untouched statements, HTML exports, and required upstream sidecars in
   raw evidence.

## Plan The Intake

Before running intake for a known legacy or manually named source, update
`analysis/issues/source_label_map.csv` when the automatic content-based route
should yield to a stable operator-managed source label. The map applies to
source-scoped destinations under both `evidence/raw/source/` and `working/`.

Run:

```bash
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot source intake plan \
  --incoming-dir <incoming_dump> \
  --workspace-root <workspace> \
  --report-dir <workspace>/working/supporting_artifacts/intake/<capture_label>
```

Review:

- `intake_plan.csv`
- `intake_issues.csv`
- `intake_summary.json`

Confirm that `source_resolution_status`, `source_resolution_reason`, and the
final `target_path` align with the intended stable source label before apply.

## Apply The Intake

Run:

```bash
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot source intake apply \
  --incoming-dir <incoming_dump> \
  --workspace-root <workspace> \
  --report-dir <workspace>/working/supporting_artifacts/intake/<capture_label>
```

Apply only after the plan artifacts look correct.

Review:

- `capture.json`
- `manifest.csv`
- `analysis/inventory/source_captures.csv`
- `analysis/issues/source_inventory.csv`

## Build The Capture Manifest

If the capture is already settled under
`evidence/raw/source/<source>/<capture_label>/`, run:

```bash
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot source manifest \
  --source-dir <workspace>/evidence/raw/source/<source>/<capture_label> \
  --output <workspace>/evidence/raw/source/<source>/<capture_label>/manifest.csv
```

Keep `manifest.csv` inside the settled capture folder.

## Profile The Capture

Run:

```bash
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot source profile \
  --source <source> \
  --raw-dir <workspace>/evidence/raw/source/<source>/<capture_label>
```

When the raw capture lives inside the workspace, the default output root is
`working/normalized/captures/<capture_uid>/`.

Review:

- `profile.json`
- `profile_inventory.csv`
- `timezone_issues.csv`

## Normalize And Assemble

Run:

```bash
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot source normalize \
  --source <source> \
  --raw-dir <workspace>/evidence/raw/source/<source>/<capture_label>
```

Then assemble the accepted capture outputs into the source dataset used by
reconciliation:

```bash
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot source assemble \
  --source <source> \
  --workspace-root <workspace>
```

Use [Normalize, Screen, And Stage](normalize-screen-stage.md) for the next
step after the settled capture has been profiled and normalized.
