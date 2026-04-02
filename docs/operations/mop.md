# Method Of Procedure

Use `docs/operations/operations-quickstart.md` when you want the short
operational path. Use this file when you need the full procedure and
supporting detail.

## Objective

Use this runbook for the current operator workflow. The typed package manages
evidence, normalization, staging, verification, and review artifacts in the
external workspace, while manual CoinTracking steps still remain part of the
current round-close process.

## Working Principles

- CoinTracking remains part of the current operator workflow for repairs and
  imports, but it is not the long-term architecture center.
- Raw exports are immutable.
- One source at a time. No multi-source imports before verification.
- The typed package should do the mechanical work; ambiguous cases stay visible
  as issues or review records.
- A blocked gate is a valid outcome. Review the artifacts before retrying.

## Workflow

### 1. Lock The Baseline

Run `baseline validate` against the oracle CoinTracking export folder and
review the generated reconciliation package.

### 2. Capture Raw Evidence

- for new incoming dumps, run `source intake plan` and review the intake reports first
- run `source intake apply` only after the plan looks correct
- keep the settled raw files under `evidence/raw/source/<source>/<capture_id>/`
- run `source manifest`
- keep `manifest.csv` inside the capture folder

### 3. Profile And Normalize

- run `source profile`
- review `profile.json`, `profile_inventory.csv`, and `timezone_issues.csv`
- run `source normalize`
- review `exceptions.csv` and `normalization_reviews.csv`
- run `output render file` when you need `cointracking_candidate.csv`

### 4. Screen And Stage

- run `batch screen`
- do not proceed while `stage_summary.json` reports `passed: false`
- run `batch stage` only after the candidate passes the screen

### 5. Seed And Execute The Round

- run `round scaffold`
- make the manual CoinTracking repair or import
- save the fresh verification export set in `working/verification/<round_id>/`

### 6. Verify

- run `verification compare`
- review the comparison package
- update issue and source-tracking files
- update the round log

### 7. Reconcile When Needed

Use `source diff` when you need a deterministic comparison between the
candidate or reference source slice and a reference ledger slice.

## Supporting Artifacts

Use `supporting extract-pdf-balances` for supported Coinbase, Binance, and
Shakepay PDF statements when balance evidence is only available in PDF form.
