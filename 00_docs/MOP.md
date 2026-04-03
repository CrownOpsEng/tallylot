# Method of Procedure (MOP)

## Objective

Use **CoinTracking.info** as the active ledger system to:

1. lock and repair the existing baseline through **2023-08-05 08:34:04**
2. import all new transactions through **2025-12-31 23:59:59**
3. export fresh verification views after each repair or import step
4. verify every round before moving forward
5. freeze a clean historical checkpoint at **2025-12-31**

This repo is the evidence, staging, and verification workspace for that process.

## Working principles

- **CoinTracking remains the system of record for imports and corrections.**
- **CRA primary guidance is the tax-law anchor for Canadian treatment questions.**
- **The canonical baseline is the full export in `01_raw_exports/portfolio/cointracking/2023-08-05_full_export/`.**
- **The authoritative cutoff is the latest Trade Table timestamp: `2023-08-05 08:34:04`.**
- **The delta window starts strictly after that cutoff.**
- **Raw exports are immutable.**
- **One source at a time. No multi-source imports before verification.**
- **Heavy reports are forensic tools, not default exports.**
- **AI may classify and compare evidence, but it must not invent transfer pairing or tax treatment.**
- **When the working tax guide is not enough, use the smallest relevant CRA source rather than broad web research.**
- **If required books and records are missing for a Canadian tax position, the issue stays open until documented or repaired.**
- **Unexplained negative fiat balances are not auto-accepted.**
- **Shakepay stays full-detail through `2025-12-31`. Any 2026 aggregation stays outside this project.**

## Folder workflow

### Raw data

- `01_raw_exports/portfolio/cointracking/2023-08-05_full_export/` → canonical CoinTracking baseline export
- `01_raw_exports/portfolio/cointracking/history/<capture_id>/` → later CoinTracking portfolio-system exports and saved report bundles
- `01_raw_exports/source/<source>/<capture_id>/` → untouched external source capture
- `01_raw_exports/source/<source>/<capture_id>/manifest.csv` → file manifest for that source capture

The `source` and `portfolio` branches are sibling roots by design. Portfolio-system outputs are verification and reconciliation evidence, not import-source truth.

### Working area

- `02_working/normalized/` → profiled raw sources, canonical outputs, exception sets, and rendered working candidates
- `02_working/import_batches/` → reviewed import candidates for the next CoinTracking step
- `02_working/verification/<round_id>/` → fresh CoinTracking exports captured after a repair or import round

### Analysis and control files

- `00_docs/BASELINE_VALIDATION.md` → durable baseline integrity summary
- `00_docs/TAX_REFERENCE_MAP.md` → targeted CRA source routing for edge cases and tax-position validation
- `03_analysis/issues/issue_log.csv` → master issue register with proof and action fields
- `03_analysis/issues/source_inventory.csv` → live source inventory for post-cutoff activity
- `03_analysis/inventory/wallet_inventory.csv` → compact canonical wallet and public-account identifier inventory
- `03_analysis/reconciliation/` → asset snapshot and exchange reconciliation artifacts
- `05_outputs/logs/round_log.csv` → structured round-by-round execution log

### Final outputs

- `04_import_ready/` → final accepted import files
- `05_outputs/checkpoints/` → frozen checkpoint export packages
- `05_outputs/reports/` → final closeout summaries and supporting reports

## Naming standard

- Raw external source files: `<YYYY-MM-DD>_<source>_<window_or_note>.<ext>`
- Verification folders: `baseline_repair_round_<nn>` or `post_import_<source>_<nn>`
- Import-ready files: `<YYYY-MM-DD>_<order>_<source>_import.<ext>`

Paths shown with angle brackets are runtime placeholders. Their parent directories are already scaffolded in the repo.

If an external platform only allows second-level export windows, use the earliest safe second after the cutoff for the export query, then still run overlap checks against the baseline Trade Table.

## Phase 0 — Lock the baseline

Purpose: make the baseline explicit and durable before any repair or extension work.

Use:

- `00_docs/BASELINE_VALIDATION.md`
- `00_docs/PROJECT_STATE.md`
- `03_analysis/reconciliation/baseline_asset_snapshot.csv`
- `03_analysis/reconciliation/baseline_exchange_reconciliation.csv`
- `03_analysis/reconciliation/baseline_source_activity.csv`
- `03_analysis/reconciliation/baseline_cad_flow_by_type.csv`
- `03_analysis/reconciliation/baseline_cad_balance_by_exchange.csv`
- the canonical exports in `01_raw_exports/portfolio/cointracking/2023-08-05_full_export/`

Do:

1. Confirm the baseline source path and manifest.
2. Confirm the authoritative cutoff timestamp from the Trade Table.
3. Confirm Current Balance and Balance by Exchange reconcile at the asset-quantity level.
4. Confirm source-level boundary evidence is captured separately from the global cutoff and do not treat the package-wide `last sync` label as proof that every source was current to the same timestamp.
5. Confirm the CAD / fiat layer is reviewed and tracked as **FIAT-001** until resolved.
6. Confirm the current known exception set is captured in `03_analysis/issues/issue_log.csv`.

Gate:

- baseline path agreed
- cutoff timestamp agreed
- baseline validation artifacts current
- source-boundary treatment explicitly tracked
- fiat-layer exception explicitly tracked

## Phase 1 — Baseline issue triage and evidence intake

Purpose: clear or classify baseline exceptions before delta imports.

Use:

- `03_analysis/issues/issue_log.csv`
- `01_raw_exports/source/<source>/<capture_id>/`
- `01_raw_exports/source/<source>/<capture_id>/manifest.csv`
- `Validate Transactions`
- `Missing Transactions` reviewed with strict settings: `100%` amount accuracy, only `100%` matches hidden, time accuracy `-24h | +48h`
- `Trade Table`

Do:

1. Review all open P1 issues first.
2. Pull the exact external evidence needed for each item, including fiat deposit, withdrawal, bank, or e-transfer evidence for **FIAT-001**.
3. Save raw files into `01_raw_exports/source/<source>/<capture_id>/`.
4. Run `06_scripts/source_manifest.py` to capture a manifest for each new raw source folder.
5. Update `proof_path` and `proof_summary` in the issue log before changing CoinTracking.

Gate:

- every open P1 item has a source, a proof path, and an intended treatment

## Phase 2 — Baseline repair inside CoinTracking

Purpose: repair the baseline before adding new years.

Use on platform:

- edit only the affected transactions inside CoinTracking

Log first:

1. create a round folder in `02_working/verification/<round_id>/`
2. seed the round log with `06_scripts/round_scaffold.py`

After each repair cluster, export these fresh to the round folder:

1. `Validate Transactions`
2. `Missing Transactions` using strict settings: `100%` amount accuracy, only `100%` matches hidden, time accuracy `-24h | +48h`
3. `Duplicate Transactions`
4. `Current Balance`
5. `Balance by Exchange`

Export only when needed:
6. `Trade Table`
7. `Roll Forward in CAD`
8. `Double-entry`

Do:

1. Record the CoinTracking change in `cointracking_action`.
2. Capture fresh exports into the round folder.
3. Review the fresh exports.
4. Update `verification_path`, `gate_result`, and `closed_at` where applicable in the issue log.
5. Update `05_outputs/logs/round_log.csv`.

Gate:

- duplicate report remains clean
- validation errors are cleared or explicitly accepted
- missing transaction report is reduced to documented non-economic spam or zero
- fiat-layer treatment is documented and no longer ambiguous

## Phase 3 — Define the delta source inventory

Purpose: list every source with post-cutoff activity before pulling exports.

Use:

- `03_analysis/issues/source_inventory.csv`
- your real-world account list
- baseline `Trade Table`
- `Balance by Exchange`

Do:

1. Review all known platforms and wallets with possible activity after `2023-08-05 08:34:04`.
2. Add one row per source to `source_inventory.csv`.
3. Record status, window, capture path, and planned import order.
4. Update the row again every time the source is confirmed active, excluded, exported, readied, imported, or closed.

Gate:

- the source inventory covers every source with possible post-cutoff activity

## Phase 4 — Pull raw delta exports

Purpose: collect import candidates without mutating the ledger yet.

Target window:

- start: strictly after `2023-08-05 08:34:04`
- end: `2025-12-31 23:59:59`

Do:

1. Export raw activity for one source at a time.
2. Save untouched files into `01_raw_exports/source/<source>/<capture_id>/`.
3. Run `06_scripts/source_manifest.py`.
4. Update `source_inventory.csv` with the export window and capture path.
5. Do not import yet.

Gate:

- raw delta exports and manifest exist for the source being prepared

## Phase 5 — Pre-import prep using AI

Purpose: prevent overlap and format mistakes before CoinTracking imports.

Use:

- baseline `Trade Table`
- source raw exports
- `02_working/normalized/`
- `02_working/import_batches/`

AI tasks allowed:

- detect date overlap with the baseline
- detect likely duplicates in new source exports
- help classify unclear rows
- highlight likely transfer pairs
- prepare a clean import candidate file

AI tasks not allowed:

- blind ledger rewrites
- assumed tax treatment without evidence
- deleting rows without documentation

Do:

1. Run `06_scripts/profile_source.py` to fingerprint the raw source and classify file families.
2. Review the generated wallet inventory artifacts for wallet-scoped sources and refresh the repo-wide inventory if the profile output lives outside the repo.
3. Run `06_scripts/normalize_source.py` to produce canonical events, canonical balances, exceptions, and a rendered working candidate under `02_working/normalized/<source>/`.
4. Review `exceptions.csv`; unresolved exceptions stay out of the import path unless they are explicitly accepted and persisted.
5. Run `06_scripts/stage_import_batch.py` to enforce overlap screening before a candidate enters `02_working/import_batches/<source>/`.
6. Copy the approved staged file to `04_import_ready/`.

Gate:

- import file reviewed
- overlap screened
- normalized candidate not confused with an approved import batch
- source inventory row updated to ready-for-import

## Phase 6 — Controlled CoinTracking import

Purpose: extend the ledger cleanly.

Recommended order:

1. Coinbase
2. Gemini / smaller sources
3. wallet sources
4. Binance
5. Shakepay last

For each source:

1. seed a round with `06_scripts/round_scaffold.py`
2. import only that source into CoinTracking
3. immediately export the default verification set into `02_working/verification/<round_id>/`
4. run `06_scripts/verification_compare.py` against the prior state and write the comparison package into the round folder
5. review the results before touching the next source

Required export set:

1. `Validate Transactions`
2. `Missing Transactions` using strict settings: `100%` amount accuracy, only `100%` matches hidden, time accuracy `-24h | +48h`
3. `Duplicate Transactions`
4. `Current Balance`
5. `Balance by Exchange`

Conditional exports:
6. `Trade Table`
7. `Roll Forward in CAD`
8. `Double-entry`

Gate:

- no unexplained duplicates
- no unexplained validation increase
- no unexplained missing transaction increase
- asset and exchange balances move as expected for the imported source
- source inventory row updated to reflect the new execution state

## Phase 7 — Final 2025 closeout

Purpose: freeze the historical ledger at `2025-12-31`.

Final export path:

- `05_outputs/checkpoints/2025-12-31_final/`

Final export set:

- `Trade Table`
- `Current Balance`
- `Balance by Exchange`
- `Validate Transactions`
- `Missing Transactions` using strict settings: `100%` amount accuracy, only `100%` matches hidden, time accuracy `-24h | +48h`
- `Duplicate Transactions`
- `Double-entry`
- `Roll Forward in CAD`
- `Realized and Unrealized Gains in CAD`

Final checks:

1. all source rows in `source_inventory.csv` are complete or intentionally excluded
2. all unresolved items are documented in `issue_log.csv`
3. the round log shows a verification package for every repair and import round
4. the fiat layer is reconciled or explicitly documented with supporting evidence
5. 2026 activity is excluded from the closeout package

## Hard stop conditions

Stop immediately if any of the following appear after a repair or import:

- duplicate report is no longer clean
- validation errors increase unexpectedly
- missing transaction count increases without explanation
- a major asset balance moves in a way the imported source cannot explain

When that happens:

1. do not touch the next source
2. capture fresh verification exports
3. log the issue in `03_analysis/issues/issue_log.csv`
4. update `05_outputs/logs/round_log.csv`
5. resolve before continuing

## Definition of done

This project is done when:

- baseline issues are repaired or intentionally documented with evidence
- all post-cutoff activity through `2025-12-31` is handled
- each source import has a verification package in this repo
- final 2025 checkpoint exports are frozen in `05_outputs/checkpoints/2025-12-31_final/`
- 2026 onward is intentionally outside this historical closeout workflow
