---
title: "Source Intake"
summary: "Detailed procedure for planning, applying, manifesting, and profiling a settled source capture."
doc_type: guide
audience: human
owner: repo
status: active
---

Use this guide when you need the detailed typed intake procedure for one source
capture.

## Start From A Settled Capture

1. Start from an untouched incoming dump when the capture is not already in the
   workspace.
2. Keep settled raw files under
   `evidence/raw/source/<source>/<capture_id>/`.
3. Do not rename or reshape raw evidence after it becomes the settled capture.

## Plan The Intake

Run:

```bash
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot source intake plan \
  --incoming-dir <incoming_dump> \
  --workspace-root <workspace> \
  --report-dir <workspace>/working/supporting_artifacts/intake/<capture_id>
```

Review:

- `intake_plan.csv`
- `intake_issues.csv`
- `intake_summary.json`

## Apply The Intake

Run:

```bash
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot source intake apply \
  --incoming-dir <incoming_dump> \
  --workspace-root <workspace> \
  --report-dir <workspace>/working/supporting_artifacts/intake/<capture_id>
```

Apply only after the plan artifacts look correct.

## Build The Capture Manifest

If the capture is already settled under
`evidence/raw/source/<source>/<capture_id>/`, run:

```bash
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot source manifest \
  --source-dir <workspace>/evidence/raw/source/<source>/<capture_id> \
  --output <workspace>/evidence/raw/source/<source>/<capture_id>/manifest.csv
```

Keep `manifest.csv` inside the settled capture folder.

## Profile The Capture

Run:

```bash
UV_PROJECT_ENVIRONMENT="$HOME/.venvs/tallylot-py312" uv run tallylot source profile \
  --source <source> \
  --raw-dir <workspace>/evidence/raw/source/<source>/<capture_id> \
  --output-dir <workspace>/working/normalized/<source>
```

Review:

- `profile.json`
- `profile_inventory.csv`
- `timezone_issues.csv`

Use [Normalize, Screen, And Stage](normalize-screen-stage.md) for the next
step after the settled capture has been profiled.
