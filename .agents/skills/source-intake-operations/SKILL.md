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
   - `docs/guides/normalize-screen-stage.md`
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
   - `make cli ARGS='source assemble'` before reconciliation or downstream
     balance work; it is the assembled source command surface the operator
     guides require after normalization
   - `make cli ARGS='checkpoint extract-pdf-balances'` when supported
     statement PDFs need the standalone statement parser path
   - `make cli ARGS='checkpoint scaffold-balance-submission'` and
     `make cli ARGS='checkpoint submit-balances'` when normalization did not
     already emit the needed balance outputs
   - `make cli ARGS='reconciliation balances check'` once assembled source
     balance outputs are ready; use the repo-local
     `reconciliation-balance-operations` skill when the task expands into the
     broader inspect/check/summarize workflow
   - `make cli ARGS='output render file'` when the round needs an external
     output artifact such as `cointracking_candidate.csv`
   - hand off to the repo-local `round-verification-operations` skill and
     `.claude/commands/round-verification.md` once a rendered candidate must
     move through oracle screening, staging, or round-close verification
   - `make cli ARGS='checkpoint rebuild-location-inventory'` only when
     normalization produced wallet evidence that needs the aggregate location
     inventory outputs
   - When the incoming evidence needs a stable source label, seed
     `analysis/issues/source_inventory.csv` and an explicit
     `analysis/issues/source_label_map.csv` row first; the planner uses the
     incoming directory name as the capture scope.
   - `make validate-workspace-replay` remains developer-only proof tooling for
     replay parity; it is not part of the ordinary operator flow
3. Review the emitted plan, profile, normalization, and issue artifacts before
   moving to the next stage.
4. Review rebuilt location inventory outputs only when normalization produced
   wallet evidence.

## Focus

- plan before apply
- inspect artifacts between stages
- keep evidence outside the repo
