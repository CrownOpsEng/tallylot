# Scripts

Use this folder for small helpers that reduce manual work without hiding logic.

Current helpers:

- `inspection.py` → shared delimiter-aware file inspection, file-family classification, timestamp extraction, and historical-date inference
- `scope_identity.py` → shared content-first scope extraction and inventory-aware scope labeling across inspection, package resolution, and intake reporting
- `archive_handling.py` → shared archive member inspection, crypto-record detection, and deterministic extraction helpers for intake
- `package_resolution.py` → shared bundle/package consolidation and same-cycle merge rules so strict duplicate packages can be skipped and warranted near-duplicate packages can be merged deterministically without crossing export cycles
- `routing.py` → shared role-based routing for historical intake dumps and canonical destination resolution across sibling `source` and `portfolio` raw-export branches
- `inventory_resolution.py` → inventory-backed source/account resolution used by intake routing so content-derived wallet scope can reuse existing repo naming instead of inventing new folders
- `overlap_engine.py` → shared overlap services for raw-evidence hash matching and CoinTracking candidate/baseline overlap checks
- `pipeline.py` → shared orchestration layer used by the CLI entrypoints
- `adapter_protocol.py` → explicit adapter capability contract used by tests and future plugin extraction work
- `baseline_check.py` → derive the baseline cutoff, counts, negative balances, and reconciliation artifacts
- `intake_sort.py` → dry-run or apply canonical routing for a mixed historical dump under `01_raw_exports/incoming/`
- `profile_source.py` → inspect a raw source folder, classify file families, and write `profile.json`, `profile_inventory.csv`, plus `timezone_issues.csv`
- `normalize_source.py` → convert a raw source folder into canonical events, canonical balances, exceptions, and a cached CoinTracking candidate after timezone validation; optional normalization-window filters are explicit rather than implicit
- `normalization_common.py` → shared canonical-event helpers, including deterministic fee attachment and exact-by-default fee matching used across adapters
- `render_cointracking.py` → translate canonical events into a CoinTracking-ready CSV with reconciliation metadata
- `stage_import_batch.py` → enforce overlap-screen approval before copying a candidate into `02_working/import_batches/` and optional `04_import_ready/`, reusing the candidate's normalization summary window when present
- `reconcile_source.py` → compare canonical source outputs against a CoinTracking Trade Table slice and optional Balance by Exchange slice
- `source_manifest.py` → build a deterministic manifest for one external source capture folder
- `wallet_inventory.py` → build the canonical wallet inventory, evidence rows, and identifier issues from the source capture set
- `overlap_check.py` → screen a CoinTracking-ready import batch for cutoff overlap and baseline duplicate risk
- `pdf_balance_extract.py` → extract deterministic balance rows from supported statement PDFs without guessing across unrelated PDFs
- `round_scaffold.py` → create a verification round folder and seed the structured round log
- `verification_compare.py` → compare two verification export folders and write deterministic drift artifacts
- `adapter_pack_scaffold.py` → scaffold a new adapter-pack fixture with canonical raw/expected layout
- `golden_refresh.py` → refresh adapter-pack goldens from current pipeline behavior
- `script_common.py` → generic file, CSV, datetime, and JSON helpers used by the shared modules
- `pipeline_common.py` / `source_adapters.py` → canonical schema definitions and adapter implementations over the shared inspection/orchestration stack

All scripts use only the Python standard library.

Current deterministic universal adapters:

- `coinbase` → ready on the current repo exports
- `wealthsimple` → ready for the crypto `activities-export` workflow
- `binance` → ready for the main spot / funding / fiat / reward paths and intentionally leaves a compact `exceptions.csv` review set for ambiguous grouped rows instead of guessing
- `shakepay` → ready on the captured cash, crypto, and performance-report exports
- `ledger_live` → ready on the captured Ledger Live operations exports, including grouped swap handling and delegation de-duplication
- `crypto_com` → ready on the captured cash and crypto transaction exports
- `near` → ready on the current NEAR transaction/token/NFT export set
- `evm_explorer` → explorer-family adapter for EVM CSV exports; ready for the BSC and primary Ethereum transfer/token scopes, and intentionally leaves suspicious standalone NFT airdrops in `exceptions.csv` instead of auto-importing them as deposits
- `gtrade` → report-level adapter for realized PnL rows and intentionally leaves open-position rows in `exceptions.csv` until companion explorer evidence exists

Wallet identification is now adapter-owned as well: `wallet_inventory.py` profiles each source capture, resolves the adapter from the profile, and only then asks that adapter to emit wallet evidence. Shared scripts no longer decide wallet behavior from source-label heuristics.

The intake pipeline is intentionally not a blind importer. `normalize_source.py` can produce a CoinTracking candidate, but that candidate is still a staging artifact. Internal wallet shuffles, unsupported rows, and ambiguous groups must stay visible through `exceptions.csv`, `issue_log.csv`, and the round-verification workflow rather than being auto-reconciled by the script layer.

The explorer adapter is keyed to the export system and chain scope rather than a wallet-app label. The adapter only promotes rows that can be justified from the underlying explorer CSV families and leaves missing-evidence gaps visible instead of guessing.

Preferred raw-capture layout:

- `01_raw_exports/source/<source>/<capture_id>/` for one evidence batch, with `<capture_id>` usually `YYYY-MM`
- `manifest.csv` inside that same capture folder
- bundle-aware placement under each capture, for example `<capture_id>/<bundle_id>/archive/...` and `<capture_id>/<bundle_id>/contents/...`
- chain-first explorer folder names such as `eth-ledger1`, `eth-gala1`, `eth-metamask1`, `polygon-metamask1`, and `bsc-metamask1`
- aggregate or app folders for wallet-app-wide evidence that is not truly chain-scoped, such as cross-chain MetaMask portfolio snapshots or state logs
- generic wallet folders only when the repo inventory cannot justify a known source name; in that case the folder should stay deterministic and identifier-based rather than guessing a friendly alias
- portfolio-system exports route separately from source evidence under `01_raw_exports/portfolio/`
- working derivatives route into `02_working/supporting_artifacts/<source>/`
- saved HTML export sidecars inherit the parent HTML export timestamp and stay in the same canonical bundle instead of being treated as standalone undated files

The preferred prep flow is now:

1. `intake_sort.py` when starting from a mixed dump
   It inspects archives independently, preserves the original archive, extracts positively identified crypto-report members into the same canonical bundle, suppresses fully redundant package copies when a deterministic superset exists, only merges near-duplicate packages when the shared package-resolution engine can prove they belong to the same export cycle, resolves wallet-style source naming from content scope before filename labels, and routes non-export artifacts into source-aware supporting-artifact folders instead of leaving them mixed into raw evidence.
2. `source_manifest.py`
3. `profile_source.py`
4. `wallet_inventory.py` when wallet evidence changed
5. `normalize_source.py`
6. `render_cointracking.py` only when a separate render step is needed
7. `stage_import_batch.py`
8. `reconcile_source.py`

`normalize_source.py` now preserves the full canonical event set by default. Use `--window-start` / `--window-end` only when you intentionally want a trimmed normalization artifact. `stage_import_batch.py` now reuses the sibling `normalization_summary.json` window by default, falls back to `--normalization-summary` when supplied, and only falls back to the repo-default post-baseline import window when no normalization summary is available.

`profile_source.py` no longer refreshes repo-wide wallet inventory as a side effect. Wallet inventory remains required repo workflow state, but it is now refreshed explicitly through `wallet_inventory.py`.

## Tests

Run the script suite from the repo root:

```bash
python3 -m pytest
```

Coverage is split into:

- `tests/adapters/` for adapter-boundary and adapter-pack expectations
- `tests/pipeline/` for orchestration and intake coverage
- `tests/unit/` for individual helper and script-function behavior
- `tests/e2e/` for CLI-level script execution
- `tests/support/` for shared test helpers
- `tests/fixtures/adapter_packs/<adapter>/<scenario>/` for adapter-owned raw inputs plus golden normalize and wallet expectations

The suite is fully `pytest` now. The adapter-pack harness enforces that:

- every supported normalization adapter ships at least one normalization pack
- every adapter with custom wallet extraction ships at least one wallet pack
- CLI normalization tests assert full golden outputs, not just file creation

Useful focused commands:

- `python3 -m pytest tests/adapters`
- `python3 -m pytest tests/pipeline`
- `python3 -m pytest tests/unit/test_source_fixture_packs.py`
- `python3 -m pytest tests/e2e/test_scripts.py -m e2e`

Open follow-up items that are intentionally out of scope for the current test-strengthening branch are tracked in [00_docs/TEST_SUITE_FOLLOWUPS.md](../00_docs/TEST_SUITE_FOLLOWUPS.md).

## Timezone Integrity

The profiling and normalization flow now records timezone provenance per dated file and refuses normalization when a source presents unresolved timezone conflicts or unsupported timestamp semantics. See `00_docs/TIMEZONE_VALIDATION.md` for the current source-by-source policy map.

## Wallet Inventory

Run `wallet_inventory.py` explicitly after adding wallet-scoped evidence or changing wallet-source profiling. The canonical artifacts live under `03_analysis/inventory/`, and they are rebuilt from the active source inventory plus adapter-owned wallet extraction logic.
