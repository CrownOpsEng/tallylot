# Operations Quickstart

Use this file for the shortest safe path through a normal operator session.
Use `docs/MOP.md` when you need the long-form procedure or supporting detail.

## Start Of Session

1. Confirm the current runtime surface in `docs/PROJECT_STATE.md` if the repo
   has changed since the last session.
2. Confirm the baseline contract in `docs/BASELINE_VALIDATION.md`.
3. Review `analysis/issues/issue_log.csv` and
   `analysis/issues/source_inventory.csv`.
4. Review the latest baseline reconciliation package under
   `analysis/reconciliation/`.
5. Confirm the current baseline export path and cutoff before touching a
   source or staging a candidate.

## Intake A Source

1. Start from an untouched incoming dump when the capture is not already in the
   workspace.
2. Plan the intake first:

   ```bash
   uv run crypto-reconciliation source intake plan \
     --incoming-dir <incoming_dump> \
     --workspace-root <workspace> \
     --report-dir <workspace>/working/supporting_artifacts/intake/<capture_id>
   ```

3. Review `intake_plan.csv`, `intake_issues.csv`, and `intake_summary.json`.
4. Apply the intake only after the plan looks correct:

   ```bash
   uv run crypto-reconciliation source intake apply \
     --incoming-dir <incoming_dump> \
     --workspace-root <workspace> \
     --report-dir <workspace>/working/supporting_artifacts/intake/<capture_id>
   ```

5. If the capture is already settled in `evidence/raw/source/<source>/<capture_id>/`,
   build the capture manifest:

   ```bash
   uv run crypto-reconciliation source manifest \
     --source-dir <workspace>/evidence/raw/source/<source>/<capture_id> \
     --output <workspace>/evidence/raw/source/<source>/<capture_id>/manifest.csv
   ```

6. Profile the capture:

   ```bash
   uv run crypto-reconciliation source profile \
     --source <source> \
     --raw-dir <workspace>/evidence/raw/source/<source>/<capture_id> \
     --output-dir <workspace>/working/normalized/<source>
   ```

7. Review `profile.json`, `profile_inventory.csv`, and `timezone_issues.csv`.

## Normalize, Screen, And Stage

1. Normalize the capture:

   ```bash
   uv run crypto-reconciliation source normalize \
     --source <source> \
     --raw-dir <workspace>/evidence/raw/source/<source>/<capture_id> \
     --output-dir <workspace>/working/normalized/<source>
   ```

2. Review:
   - `canonical_events.csv`
   - `exceptions.csv`
   - `normalization_reviews.csv`
   - `cointracking_candidate.csv`

3. Screen the candidate:

   ```bash
   uv run crypto-reconciliation batch screen \
     --candidate <workspace>/working/normalized/<source>/cointracking_candidate.csv \
     --baseline-export-dir <workspace>/evidence/raw/portfolio/cointracking/2023-08-05_full_export \
     --output-dir <workspace>/working/import_batches/<source>
   ```

4. If the screen passes, stage the same candidate with `batch stage`.
5. If it blocks, review `stage_issues.csv` and `stage_summary.json` before
   changing anything manually.
6. Use `source reconcile` when the candidate needs a direct row diff against a
   reference export before import.

## Seed And Verify A Round

1. Seed the round:

   ```bash
   uv run crypto-reconciliation round scaffold \
     --round-id <round_id> \
     --phase <phase> \
     --source <source>
   ```

2. Make the manual CoinTracking change or import.
3. Save the fresh verification export set under `working/verification/<round_id>/`.
4. Compare against the prior verified state:

   ```bash
   uv run crypto-reconciliation verification compare \
     --previous-dir <prior_verification_dir> \
     --current-dir <workspace>/working/verification/<round_id> \
     --output-dir <workspace>/working/verification/<round_id>/comparison
   ```

5. Update `analysis/issues/issue_log.csv`, `analysis/issues/source_inventory.csv`
   when relevant, and `outputs/logs/round_log.csv`.
6. Do not advance to the next source until the current round is verified.
