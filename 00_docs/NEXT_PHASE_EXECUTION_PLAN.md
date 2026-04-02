# Next Phase Execution Plan

This document is the working checklist for the post-baseline phase of the project.

Baseline repair is complete enough to move forward. The current clean state is:

- `Validate Transactions`: `0` rows
- strict `Missing Transactions`: only the already-accepted `MISS-013` and `MISS-015` Binance returned-transfer exception pair
- no active baseline repair items remain

The project still follows the canonical cutoff:

- start strictly after `2023-08-05 08:34:04`
- end at `2025-12-31 23:59:59`

## Execution Rules

1. Import one source at a time.
2. Do not import any source until its round is seeded in `05_outputs/logs/round_log.csv`.
3. For every import round, export only the default verification set unless drift forces heavier reports.
4. Do not move to the next source until the current round has a comparison package and a recorded gate result.
5. Reopen fiat review only if a source changes CAD or another fiat layer in a way that conflicts with the current documented treatment.

## Source Queue

| Order | Source | Current status | Next concrete action | Round target |
| --- | --- | --- | --- | --- |
| 1 | Coinbase | `capture_complete` | Verify whether the Coinbase all-time export fully subsumes historical Coinbase Pro coverage, then build the post-cutoff candidate | `post_import_coinbase_01` |
| 2 | WealthSimple | `capture_complete` | Trim to the project window, normalize for CoinTracking, and overlap-screen | `post_import_wealthsimple_01` |
| 3 | ledger-live-main | `capture_complete` | Normalize the capture-local Ledger Live files and overlap-screen the candidate | `post_import_ledger_live_main_01` |
| 4 | bsc-metamask1 | `capture_complete` | Normalize the capture-local explorer files and overlap-screen the candidate | `post_import_bsc_metamask1_01` |
| 5 | Binance | `capture_complete` | Classify the residual WBETH dust treatment, trim all candidates to `<= 2025-12-31`, then overlap-screen | `post_import_binance_01` |
| 6 | Shakepay | `capture_complete` | Prepare the final import tranche and keep it last per project procedure | `post_import_shakepay_01` |

## Open Follow-Ups

These items stay in view while imports proceed:

- `SRC-003`: Coinbase import signoff requires confirming whether the Coinbase export already covers Coinbase Pro history.
- `BAL-001`: Binance prep requires documenting the residual `0.00001148` `WBETH` position and treating daily staking position snapshots as evidence only.
- `SRC-004`: Review Coinberry backups when the SSD enclosure is available. This is evidence follow-up, not an immediate import blocker.
- `SRC-005`: Review Kucoin backups when available. This is evidence follow-up unless a missing ledger segment appears.

## Round Workflow

Use this checklist for every source in the queue:

1. Confirm the source row in `03_analysis/issues/source_inventory.csv` is current.
2. Confirm the candidate window starts strictly after `2023-08-05 08:34:04`.
3. Capture raw files in `01_raw_exports/external/<source>/<capture_id>/` and keep `manifest.csv` inside that capture folder.
4. Run `06_scripts/source_manifest.py` against the capture folder.
5. Prepare the working import file in `02_working/import_batches/<source>/`.
6. Run `06_scripts/overlap_check.py` against the CoinTracking-ready candidate.
7. Hold the batch if overlap screening does not pass.
8. Copy the approved candidate to `04_import_ready/`.
9. Seed the round with `06_scripts/round_scaffold.py`.
10. Import exactly one source into CoinTracking.
11. Export the default verification set into `02_working/verification/<round_id>/`:
    - `Validate Transactions`
    - `Missing Transactions` with strict settings: `100%` amount accuracy, only `100%` matches hidden, time accuracy `-24h | +48h`
    - `Duplicate Transactions`
    - `Current Balance`
    - `Balance by Exchange`
12. Run `06_scripts/verification_compare.py` against the prior verified state.
13. Review the comparison package and classify any new issues before touching the next source.
14. Update `03_analysis/issues/source_inventory.csv`.
15. Update `03_analysis/issues/issue_log.csv` if any new issue or accepted exception appears.
16. Update `05_outputs/logs/round_log.csv`.

## Stop Conditions

Stop the queue immediately if any round creates:

- new unexplained duplicates
- new unexplained validation errors
- new unexplained strict missing-transaction rows
- asset or exchange balance movement that the imported source does not explain

If that happens:

1. Do not import the next source.
2. Capture the fresh exports and comparison artifacts.
3. Log the issue in `03_analysis/issues/issue_log.csv`.
4. Record the failed gate in `05_outputs/logs/round_log.csv`.
5. Resolve the drift before resuming the queue.

## Closeout Target

The queue is complete when:

1. Every in-scope source is either `complete` or intentionally excluded with evidence.
2. Every import round has a verification package and comparison folder.
3. Any unresolved item is explicitly documented in `03_analysis/issues/issue_log.csv`.
4. The final `2025-12-31` checkpoint package is frozen under `05_outputs/checkpoints/2025-12-31_final/`.
5. No `2026` activity is included in the closeout import set.
