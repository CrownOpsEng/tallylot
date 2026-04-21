---
name: source-intake-operations
description: >-
  Run tallylot's typed intake path without ad hoc shell choreography. Use when
  the task is source intake planning, apply, manifesting, profiling,
  normalization, or checkpoint inventory follow-through.
---

# Source Intake Operations

Use this skill for source intake and normalization workflow execution.

## Workflow

1. Read the operator route first:
   - `docs/guides/operator-quickstart.md`
   - `docs/guides/source-intake.md`
   - `.claude/commands/source-intake.md`
2. Use the runtime CLI, not ad hoc loops:
   - `make cli ARGS='source intake plan'`
   - `make cli ARGS='source intake apply'`
   - `make cli ARGS='source manifest'`
   - `make cli ARGS='source profile'`
   - `make cli ARGS='source normalize --update-mode auto'`
   - use `--update-mode full-update` to refresh all current stage-owned detail
     from authoritative truth while reusing unchanged kernels
   - use `--update-mode rebuild` to bypass fast-path reuse and rebuild the
     implemented target-product chain from declared upstream truth
   - When the incoming evidence needs a stable source label, seed
     `analysis/issues/source_inventory.csv` and an explicit
     `analysis/issues/source_label_map.csv` row first; the planner uses the
     incoming directory name as the capture scope.
   - `make validate-workspace-replay` remains developer-only proof tooling for
     replay parity; it is not part of the ordinary operator flow
3. Review the emitted plan, profile, normalization, and issue artifacts before
   moving to the next stage.
4. Rebuild location inventory only when normalization produced wallet evidence.

## Focus

- plan before apply
- inspect artifacts between stages
- keep evidence outside the repo
