---
title: "Operator Quickstart"
summary: "Shortest safe path through intake, normalization, staging, and verification."
doc_type: guide
audience: human
owner: repo
status: active
naming_scope: current_state
nav_order: 10
---

Use this file for the shortest safe path through a normal operator session.
Use the linked task guides when you need the detailed procedure for one stage.

## Start Of Session

1. Confirm the current runtime surface in `docs/status/current-state.md`.
2. Confirm the baseline contract in `docs/reference/baseline-validation-contract.md`.
3. Review `analysis/issues/issue_log.csv`,
   `analysis/issues/source_inventory.csv`, and the latest baseline
   reconciliation package under `analysis/reconciliation/`.
4. Confirm the current baseline export path and cutoff before touching a
   source or staging a candidate.

## Intake A Source

1. Treat one intake run as one capture and keep settled raw evidence under
   `evidence/raw/source/<source>/<capture_label>/`.
2. Run `source intake plan` before touching the workspace.
3. Run `source intake apply` only after the plan artifacts look correct. A
   non-`captured` intake outcome returns a nonzero exit code even though the
   intake report artifacts are still written for review.
4. Run `source manifest`, `source profile`, and `source normalize` against the
   settled materialized capture root. `source profile` and `source normalize`
   reject source roots, arbitrary subdirectories, and capture roots whose
   `capture.json` metadata does not match the path and source.
5. Use the default `source normalize --update-mode auto` path for ordinary
   reruns. It recalculates affected authoritative stages automatically,
   reuses unchanged kernels, rewrites the capture-local mirrors from current
   truth, and prunes stale stage-owned outputs. Use `--update-mode full-update`
   to refresh all current stage-owned detail while reusing unchanged kernels,
   and `--update-mode rebuild` to bypass reuse and rebuild the implemented
   target-product chain.
6. Run `source assemble` before any reconciliation command. Reruns rewrite the
   generated source dataset under `working/normalized/sources/<source>/` rather
   than appending stale artifacts.
7. Use [Source Intake](source-intake.md) for the detailed commands, review
   points, and artifact expectations.

## Normalize, Screen, And Stage

1. Run `source normalize` for the settled capture and review the
   capture-scoped outputs under `working/normalized/captures/<capture_uid>/`.
2. Keep replay validation developer-only. Normal operator work uses the
   automatic rerun fast path on `source normalize` rather than a separate
   replay-validation step.
3. Run `source assemble` and review the assembled source dataset under
   `working/normalized/sources/<source>/`.
4. Use `checkpoint extract-pdf-balances` when a supported statement PDF is the
   source-backed evidence path; it uses the same statement extraction service
   as normalization.
5. If normalization did not already produce `balance_snapshots.csv` and
   source-backed `balance_references.csv`, run
   `checkpoint scaffold-balance-submission`, fill the submission package, then
   run `checkpoint submit-balances` and review the submission summary and
   issues when they are present.
6. Run `reconciliation balances check` when balance outputs are ready for a
   deterministic balance check, whether they came from
   normalization or from validated manual submission with
   `operator_assertion` reference rows in `balance_references.csv`.
7. When you need a multi-source answer, run `reconciliation balances inspect`,
   then `reconciliation balances check`, then `reconciliation balances summarize`.
8. Run `output render file` only when the round needs
   `cointracking_candidate.csv`.
9. Run `batch screen`, then `batch stage` only after the screen passes.
10. Use [Normalize, Screen, And Stage](normalize-screen-stage.md) for the
   detailed command flow, artifact review, and stop conditions.

## Seed And Verify A Round

1. Run `round scaffold` before the manual repair or import step.
2. Save the fresh verification export set under
   `working/verification/<round_id>/`.
3. Run `verification compare` and review the comparison package.
4. Update issue, source, and round-log records before moving to the next
   source.
5. Use [Verify A Round](verify-a-round.md) for the detailed procedure and
   [Export Checklist](../reference/export-checklist.md) for the verification
   export set.
