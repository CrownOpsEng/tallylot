# Scripts

Use this folder for small helpers that reduce manual work without hiding logic.

Current helpers:

- `baseline_check.py` → derive the baseline cutoff, counts, negative balances, and reconciliation artifacts
- `profile_source.py` → inspect a raw source folder, classify file families, and write `profile.json` plus `profile_inventory.csv`
- `normalize_source.py` → convert a raw source folder into canonical events, canonical balances, exceptions, and a cached CoinTracking candidate
- `render_cointracking.py` → translate canonical events into a CoinTracking-ready CSV with reconciliation metadata
- `stage_import_batch.py` → enforce overlap-screen approval before copying a candidate into `02_working/import_batches/` and optional `04_import_ready/`
- `reconcile_source.py` → compare canonical source outputs against a CoinTracking Trade Table slice and optional Balance by Exchange slice
- `coinbase_normalize.py` → normalize Coinbase retail and Coinbase Pro raw exports into CoinTracking-schema transaction rows plus Coinbase PDF balance rows
- `coinbase_check.py` → compare CoinTracking Coinbase rows against normalized Coinbase exports and optional balance evidence
- `source_manifest.py` → build a deterministic manifest for a raw external source folder and refuse non-`raw/` inputs by default
- `overlap_check.py` → screen a CoinTracking-ready import batch for cutoff overlap and baseline duplicate risk
- `pdf_balance_extract.py` → extract deterministic balance rows from supported statement PDFs without guessing across unrelated PDFs
- `round_scaffold.py` → create a verification round folder and seed the structured round log
- `verification_compare.py` → compare two verification export folders and write deterministic drift artifacts
- `script_common.py` → shared CSV, path-validation, and default verification-export helpers used by the scripts
- `pipeline_common.py` / `source_adapters.py` → shared canonical schema and adapter registry for the universal intake pipeline

All scripts use only the Python standard library.

Current deterministic universal adapters:

- `coinbase` → ready on the current repo exports
- `wealthsimple` → ready for the crypto `activities-export` workflow
- `binance` → ready for the main spot / funding / fiat / reward paths and intentionally leaves a compact `exceptions.csv` review set for ambiguous legacy rows instead of guessing

The intake pipeline is intentionally not a blind importer. `normalize_source.py` can produce a CoinTracking candidate, but that candidate is still a staging artifact. Internal wallet shuffles, unsupported rows, and ambiguous groups must stay visible through `exceptions.csv`, `issue_log.csv`, and the round-verification workflow rather than being auto-reconciled by the script layer.

The preferred prep flow is now:

1. `source_manifest.py`
2. `profile_source.py`
3. `normalize_source.py`
4. `render_cointracking.py` only when a separate render step is needed
5. `stage_import_batch.py`
6. `reconcile_source.py`

`coinbase_normalize.py` and `coinbase_check.py` remain as Coinbase-specific reference tooling while the universal pipeline reaches parity on the remaining sources.

## Tests

Run the script suite from the repo root:

```bash
python3 -m unittest discover -s tests -v
```

Coverage is split into:

- `tests/unit/` for individual helper and script-function behavior
- `tests/e2e/` for CLI-level script execution
- `tests/support/` for shared test helpers
