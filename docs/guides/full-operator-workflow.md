---
title: "Full Operator Workflow"
summary: "Long-form runbook for the current operator workflow and round-close process."
doc_type: guide
audience: human
owner: repo
status: active
naming_scope: current_state
nav_order: 50
---

Use `docs/guides/operator-quickstart.md` when you want the short operational
path. Use this file when you need the full sequence and the surrounding
operating rules for a round-close session.

## Objective

Use this runbook for the current operator workflow. The typed package manages
evidence, normalization, staging, verification, and review artifacts in the
external workspace, while manual import and verification steps still remain
part of the current round-close process.

## Working Principles

- The current operator workflow still includes manual repair and import steps,
  but those are not the long-term architecture center.
- Raw exports are immutable.
- One source at a time. No multi-source imports before verification.
- The typed package should do the mechanical work; ambiguous cases stay visible
  as issues or review records.
- A blocked gate is a valid outcome. Review the artifacts before retrying.

## Workflow

### 1. Lock The Baseline

- Run `make oracle ARGS='baseline validate'`
  against the oracle baseline export folder.
- Review the generated reconciliation package before starting a new source.

### 2. Intake The Source

- Plan and apply intake before hand-shaping anything in the workspace.
- Keep the settled raw files under
  `evidence/raw/source/<source>/<capture_label>/`.
- One intake run equals one capture. Inferred periods stay metadata-only.
- Keep untouched statements, HTML exports, and required upstream sidecars in
  raw evidence.
- Build the capture manifest and profile the settled capture.
- `source profile` and `source normalize` must point at the materialized
  capture root with matching `capture.json` metadata. They do not accept source
  roots or arbitrary directories.
- Use [Source Intake](source-intake.md) for the full command sequence and
  artifact review points.

### 3. Normalize And Prepare A Candidate

- Normalize the settled capture and review the emitted issues and summaries
  under `working/normalized/captures/<capture_uid>/`.
- Review `profile_inventory.csv` as the capture-scoped discovery contract for
  statement-backed evidence, archive-member provenance, and issue and review
  routing.
- Run `source assemble` before reconciliation so the accepted capture outputs
  land under `working/normalized/sources/<source>/`.
- `source assemble` owns that source dataset surface and rewrites its known
  generated files on rerun instead of leaving stale assembled artifacts behind.
- Use normalization-owned `balance_snapshots.csv` and
  `balance_references.csv` directly when the source adapter already produced
  balance outputs.
- When balances need to be authored manually, run
  `make cli ARGS='checkpoint scaffold-balance-submission --source <source>'`,
  fill the submission package under
  `working/supporting_artifacts/balance_submissions/<source>/`, then run
  `make cli ARGS='checkpoint submit-balances --source <source>'`
  and review `balance_submission_summary.json`; review
  `balance_submission_issues.csv` when the submit run reports issues.
- Run `reconciliation balances check` once `balance_snapshots.csv` and
  `balance_references.csv` are available for the runtime balance check.
- Use normalization-owned `source_document` rows when the source is already
  source-backed.
- Use submission-owned `operator_assertion` rows when the source is only
  operator-authored so far.
- Treat source-backed checkpoint readiness separately from operator-confirmed
  runtime readiness.
- Use `reconciliation balances inspect` plus
  `reconciliation balances summarize` when you need a multi-source
  reconciliation-date answer instead of a single-source review.
- Optional submitted `location_inventory.csv` improves the additive
  cross-source corroboration sidecars written by `reconciliation balances check`.
- Render `cointracking_candidate.csv` only when the round needs an external
  comparison artifact.
- Use [Normalize, Screen, And Stage](normalize-screen-stage.md) for the
  detailed normalization, screening, staging, and diff procedure.

### 4. Screen And Stage

- Run the oracle screen before any staging step.
- Do not proceed while `stage_summary.json` reports `passed: false`.
- Stage only after the candidate passes the screen.

### 5. Seed And Execute The Round

- Run `round scaffold`.
- Make the manual repair or import in the external verification tool.
- Save the fresh verification export set in `working/verification/<round_id>/`.

### 6. Verify And Close The Round

- Run `verification compare`.
- Review the comparison package.
- Update issue, source, and round-log records before moving to the next
  source.
- Use [Verify A Round](verify-a-round.md) for the detailed verification and
  closeout procedure.

## Supporting Artifacts

- Use [Export Checklist](../reference/export-checklist.md) for the required
  verification export set.
- Use
  [Manual Balance Submission Packages](../reference/manual-balance-submission-artifacts.md)
  for the scaffolded submission package contract and balance materialization
  rules.
- Use `checkpoint extract-pdf-balances` for supported Coinbase, Binance, and
  Shakepay PDF statements when source-backed balance references are only
  available in PDF form. The command uses the same statement extraction path
  as normalization.
