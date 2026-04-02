# Scripts

Use this folder for small helpers that reduce manual work without hiding logic.

Current helpers:

- `baseline_check.py` → derive the baseline cutoff, counts, negative balances, and reconciliation artifacts
- `coinbase_normalize.py` → normalize Coinbase retail and Coinbase Pro raw exports into CoinTracking-schema transaction rows plus Coinbase PDF balance rows
- `coinbase_check.py` → compare CoinTracking Coinbase rows against normalized Coinbase exports and optional balance evidence
- `source_manifest.py` → build a deterministic manifest for a raw external source folder and refuse non-`raw/` inputs by default
- `overlap_check.py` → screen a CoinTracking-ready import batch for cutoff overlap and baseline duplicate risk
- `pdf_balance_extract.py` → extract deterministic balance rows from supported statement PDFs without guessing across unrelated PDFs
- `round_scaffold.py` → create a verification round folder and seed the structured round log
- `verification_compare.py` → compare two verification export folders and write deterministic drift artifacts
- `script_common.py` → shared CSV, path-validation, and default verification-export helpers used by the scripts

All scripts use only the Python standard library.

## Tests

Run the script suite from the repo root:

```bash
python3 -m unittest discover -s tests -v
```

Coverage is split into:

- `tests/unit/` for individual helper and script-function behavior
- `tests/e2e/` for CLI-level script execution
- `tests/support/` for shared test helpers
