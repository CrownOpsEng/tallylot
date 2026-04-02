# Next Phase Execution Plan

Use this document as a template for the next verified source round.

## Preparation

1. Confirm the source row in `analysis/issues/source_inventory.csv`.
2. If starting from a new dump, run `source intake plan` and `source intake apply`.
3. Confirm the capture path under `evidence/raw/source/<source>/<capture_id>/`.
4. Run `source manifest`, `source profile`, and `source normalize`.
5. Review timezone, exception, and normalization review artifacts.
6. Run `batch screen`.

## Round Start

1. Run `round scaffold --round-id <round_id> --phase <phase> --source <source>`.
2. If the screen passed, run `batch stage`.
3. Make exactly one CoinTracking change or import for the round.

## Verification

1. Save the default verification export set to `working/verification/<round_id>/`.
2. Run `verification compare` against the prior verified state.
3. Update issue, source, and round-log records.
4. Do not advance to the next source until the current round is verified.
