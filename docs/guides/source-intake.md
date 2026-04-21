---
title: "Source Intake"
summary: "Detailed procedure for planning, applying, manifesting, and profiling a settled source capture."
doc_type: guide
audience: human
owner: repo
status: active
naming_scope: current_state
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
Make sure the target source already exists in
`analysis/issues/source_inventory.csv`; the planner treats the incoming
directory name as the capture scope, so a scoped `source_label_map.csv` row
can match the exact staging directory when you need to override the
content-based route.

Use `incoming_capture_scope` when one workspace is staging more than one
incoming source tree at the same time. Set that scope to the operator-managed
staging directory name, then keep `incoming_path_prefix` relative to that
incoming directory. This allows multiple `.` mappings to coexist in the same
workspace as long as each mapping is scoped to a different incoming capture.

Run:

```bash
make cli ARGS='source intake plan \
  --incoming-dir <incoming_dump> \
  --workspace-root <workspace> \
  --report-dir <workspace>/working/supporting_artifacts/intake/<capture_label>'
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
make cli ARGS='source intake apply \
  --incoming-dir <incoming_dump> \
  --workspace-root <workspace> \
  --report-dir <workspace>/working/supporting_artifacts/intake/<capture_label>'
```

Apply only after the plan artifacts look correct.

`source intake apply` still writes its report artifacts before exit. When the
run finishes with a non-`captured` `capture_status` such as
`capture_blocked`, `duplicate_blocked`, or `overlap_review_required`, the CLI
returns a nonzero exit code so shell automation does not treat the outcome as
clean success.

Review:

- `intake_summary.json` and `intake_issues.csv` for every run
- `capture.json` and `manifest.csv` when the run materializes a capture under
  `evidence/raw/source/<source>/<capture_label>/`
- `analysis/inventory/source_captures.csv` when the run records a capture or
  duplicate-blocked attempt
- `analysis/issues/source_inventory.csv` when the run resolves a concrete
  source and updates source summary state

## Build The Capture Manifest

If the capture is already settled under
`evidence/raw/source/<source>/<capture_label>/`, run:

```bash
make cli ARGS='source manifest \
  --source-dir <workspace>/evidence/raw/source/<source>/<capture_label> \
  --output <workspace>/evidence/raw/source/<source>/<capture_label>/manifest.csv'
```

Keep `manifest.csv` inside the settled capture folder.

## Profile The Capture

Run:

```bash
make cli ARGS='source profile \
  --source <source> \
  --raw-dir <workspace>/evidence/raw/source/<source>/<capture_label>'
```

`source profile` requires the exact materialized capture root under
`evidence/raw/source/<source>/<capture_label>/`. The command rejects source
roots, arbitrary directories, and any root whose `capture.json` metadata does
not match the path and requested source.

When the raw capture lives inside the workspace, the default output root stays
`working/normalized/captures/<capture_uid>/`.

Review:

- `profile.json`
- `profile_inventory.csv`
- `timezone_issues.csv`

`profile_inventory.csv` is the capture-scoped discovery contract used later by
shared statement extraction and normalization issue and review routing. Review
fields such as `capture_uid`, `source`, `evidence_role`,
`observed_period_start`, `observed_period_end`, `observed_period_label`,
`statement_kind`, and `originality_class` instead of rediscovering files by
hand.

## Normalize And Assemble

Run:

```bash
make cli ARGS='source normalize \
  --source <source> \
  --raw-dir <workspace>/evidence/raw/source/<source>/<capture_label>'
```

`source normalize` has the same strict input contract as `source profile`: one
materialized capture root with matching `capture.json` metadata.
The default `--update-mode auto` path is the normal operator route: it reuses
unchanged authoritative target products, recalculates affected stages
automatically when authoritative inputs changed, refreshes required sidecars,
rewrites capture-local mirror files from current truth, and prunes stale
stage-owned outputs.

Use `--update-mode full-update` when you need every current stage-owned detail
or compatibility output refreshed from the current authoritative truth while
still reusing unchanged kernels.

Use `--update-mode rebuild` when you need to bypass fast-path reuse and rebuild
the implemented target-product chain from current declared upstream truth.

Then assemble the accepted capture outputs into the source dataset used by
reconciliation:

```bash
make cli ARGS='source assemble \
  --source <source> \
  --workspace-root <workspace>'
```

`source assemble` owns the generated artifact surface under
`working/normalized/sources/<source>/` and is safe to rerun. It rewrites its
known generated files without deleting unrelated operator-owned files beside
them.

Developer replay validation remains available for migration proof and repo-side
investigation, but it is developer-only proof tooling rather than part of the
normal operator intake flow.

Use [Normalize, Screen, And Stage](normalize-screen-stage.md) for the next
step after the settled capture has been profiled and normalized.
