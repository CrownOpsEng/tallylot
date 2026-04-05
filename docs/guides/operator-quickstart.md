---
title: "Operator Quickstart"
summary: "Shortest safe path through intake, normalization, staging, and verification."
doc_type: guide
audience: human
owner: repo
status: active
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

1. Start from an untouched incoming dump or a settled raw capture under
   `evidence/raw/source/<source>/<capture_id>/`.
2. Run `source intake plan` before touching the workspace.
3. Run `source intake apply` only after the plan artifacts look correct.
4. Run `source manifest` and `source profile` for the settled capture.
5. Use [Source Intake](source-intake.md) for the detailed commands, review
   points, and artifact expectations.

## Normalize, Screen, And Stage

1. Run `source normalize` for the settled capture.
2. Review the normalization artifacts and issues before rendering a candidate.
3. If normalization did not already produce canonical `balances.csv` and
   `balance_evidence.csv`, run
   `checkpoint scaffold-balance-submission`, fill the submission package, then
   run `checkpoint submit-balances` and review the submission summary and
   issues.
4. Run `reconciliation balances check` when canonical balance artifacts are
   ready for a deterministic balance check, whether they came from
   normalization or validated manual submission.
5. When you need a multi-source answer, run `reconciliation balances inspect`,
   then `reconciliation balances check`, then `reconciliation balances summarize`.
6. Run `output render file` only when the round needs
   `cointracking_candidate.csv`.
7. Run `batch screen`, then `batch stage` only after the screen passes.
8. Use [Normalize, Screen, And Stage](normalize-screen-stage.md) for the
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
