# Scripts

Use this folder for small helpers that reduce manual work without hiding logic.

Current helpers:

- `baseline_check.py` → derive the baseline cutoff, counts, negative balances, and reconciliation artifacts
- `profile_source.py` → inspect a raw source folder, classify file families, and write `profile.json`, `profile_inventory.csv`, plus `timezone_issues.csv`
- `normalize_source.py` → convert a raw source folder into canonical events, canonical balances, exceptions, and a cached CoinTracking candidate after timezone validation passes
- `render_cointracking.py` → translate canonical events into a CoinTracking-ready CSV with reconciliation metadata
- `stage_import_batch.py` → enforce overlap-screen approval before copying a candidate into `02_working/import_batches/` and optional `04_import_ready/`
- `reconcile_source.py` → compare canonical source outputs against a CoinTracking Trade Table slice and optional Balance by Exchange slice
- `coinbase_normalize.py` → normalize Coinbase retail and Coinbase Pro raw exports into CoinTracking-schema transaction rows plus Coinbase PDF balance rows
- `coinbase_check.py` → compare CoinTracking Coinbase rows against normalized Coinbase exports and optional balance evidence
- `source_manifest.py` → build a deterministic manifest for one external source capture folder; both the legacy `raw/` layout and capture-local manifests are supported
- `wallet_inventory.py` → build the canonical wallet inventory, evidence rows, and identifier issues from the raw capture set
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
- `shakepay` → ready on the captured cash, crypto, and performance-report exports
- `ledger_live` → ready on the captured Ledger Live operations exports, including grouped swap handling and delegation de-duplication
- `crypto_com` → ready on the captured cash and crypto transaction exports
- `near` → ready on the current NEAR transaction/token/NFT export set
- `evm_explorer` → explorer-family adapter for EVM CSV exports; ready for the BSC and primary Ethereum transfer/token scopes, and intentionally leaves suspicious standalone NFT airdrops in `exceptions.csv` instead of auto-importing them as deposits
- `gtrade` → report-level adapter for realized PnL rows and intentionally leaves open-position rows in `exceptions.csv` until companion explorer evidence exists

Wallet identification is now adapter-owned as well: `wallet_inventory.py` profiles each raw capture, resolves the adapter from the profile, and only then asks that adapter to emit wallet evidence. Shared scripts no longer decide wallet behavior from source-label heuristics.

The intake pipeline is intentionally not a blind importer. `normalize_source.py` can produce a CoinTracking candidate, but that candidate is still a staging artifact. Internal wallet shuffles, unsupported rows, and ambiguous groups must stay visible through `exceptions.csv`, `issue_log.csv`, and the round-verification workflow rather than being auto-reconciled by the script layer.

The explorer adapter is now keyed to the export system and chain scope rather than a wallet-app label. A legacy wallet-app export dump is treated as EVM explorer evidence; the adapter only promotes rows that can be justified from the underlying explorer CSV families and leaves missing-evidence gaps visible instead of guessing.

Preferred external-capture layout:

- `01_raw_exports/external/<source>/<capture_id>/` for one evidence batch, with `<capture_id>` usually `YYYY-MM`
- `manifest.csv` inside that same capture folder
- chain-first explorer folder names such as `eth-ledger1`, `eth-gala1`, `eth-metamask1`, `polygon-metamask1`, and `bsc-metamask1`
- aggregate or app folders for wallet-app-wide evidence that is not truly chain-scoped, such as cross-chain MetaMask portfolio snapshots or state logs
- the older `01_raw_exports/external/<source>/raw/` plus source-root `manifest.csv` layout still works for legacy sources while the repo transitions

The preferred prep flow is now:

1. `source_manifest.py`
2. `profile_source.py`
3. `wallet_inventory.py` when wallet evidence changed
4. `normalize_source.py`
5. `render_cointracking.py` only when a separate render step is needed
6. `stage_import_batch.py`
7. `reconcile_source.py`

`coinbase_normalize.py` and `coinbase_check.py` remain as Coinbase-specific reference tooling while the universal pipeline reaches parity on the remaining sources.

`profile_source.py` no longer refreshes repo-wide wallet inventory as a side effect. Wallet inventory remains required repo workflow state, but it is now refreshed explicitly through `wallet_inventory.py`.

## Tests

Run the script suite from the repo root:

```bash
python3 -m unittest discover -s tests -v
```

Coverage is split into:

- `tests/unit/` for individual helper and script-function behavior
- `tests/e2e/` for CLI-level script execution
- `tests/support/` for shared test helpers

## Timezone Integrity

The profiling and normalization flow now records timezone provenance per dated file and refuses normalization when a source presents unresolved timezone conflicts or unsupported timestamp semantics. See `00_docs/TIMEZONE_VALIDATION.md` for the current source-by-source policy map.

## Wallet Inventory

Run `wallet_inventory.py` explicitly after adding wallet-scoped evidence or changing wallet-source profiling. The canonical artifacts live under `03_analysis/inventory/`, and they are rebuilt from the active source inventory plus adapter-owned wallet extraction logic.
