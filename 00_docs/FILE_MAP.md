# File Map

This repo is built around the canonical CoinTracking full export stored in:

`01_raw_exports/cointracking/2023-08-05_full_export/`

## Control documents

| File | Purpose |
| ---- | ------- |
| `00_docs/MOP.md` | Operating procedure for the full reconciliation and closeout workflow |
| `00_docs/CANADIAN_CRYPTOCURRENCY_TAXATION_GUIDE.md` | CRA-aligned working tax reference for Canadian crypto treatment questions |
| `00_docs/TAX_REFERENCE_MAP.md` | Compact source-routing map to the relevant CRA authority for edge cases |
| `00_docs/OPERATIONS_QUICKSTART.md` | Shortest safe execution path for manual work plus AI/script support |
| `00_docs/BASELINE_VALIDATION.md` | Durable summary of baseline integrity and cutoff facts |
| `00_docs/TIMEZONE_VALIDATION.md` | Source-by-source timezone evidence, platform doc links, and intake-gate rules |
| `00_docs/WALLET_INVENTORY.md` | Canonical wallet-identifier inventory contract, generation flow, and review rules |
| `00_docs/NEXT_PHASE_EXECUTION_PLAN.md` | Source-by-source execution queue and round checklist for the post-baseline phase |
| `00_docs/PROJECT_STATE.md` | Current baseline counts, constraints, and decision boundary |
| `00_docs/EXPORT_CHECKLIST.md` | Smallest efficient export set for each round |

## Active working files

| File | Purpose | When used |
| ---- | ------- | --------- |
| `03_analysis/issues/issue_log.csv` | Master issue register with proof, action, and gate fields | Baseline repair, exception tracking |
| `03_analysis/issues/source_inventory.csv` | Live post-cutoff source inventory | Before any new source export or import |
| `03_analysis/inventory/wallet_inventory.csv` | Compact canonical wallet and public-account identifier inventory | Before wallet/source evidence review and source intake |
| `03_analysis/inventory/wallet_inventory_issues.csv` | Deterministic wallet-identifier review items | When a source exposes only partial or conflicting identifier evidence |
| `03_analysis/issues/README.md` | Status and field guide for the live control files | When updating issue or source states |
| `05_outputs/logs/round_log.csv` | Structured round-by-round execution log | Every repair and import round |
| `03_analysis/reconciliation/baseline_asset_snapshot.csv` | Asset-level baseline snapshot from Current Balance | Baseline lock, later comparison |
| `03_analysis/reconciliation/baseline_exchange_reconciliation.csv` | Asset reconciliation between Current Balance and Balance by Exchange | Baseline lock, drift explanation |
| `03_analysis/reconciliation/baseline_cad_flow_by_type.csv` | CAD bought, sold, and fee summary by transaction type | Fiat-layer review and closeout |
| `03_analysis/reconciliation/baseline_cad_balance_by_exchange.csv` | CAD ending balances by exchange/location | Fiat-layer review and closeout |

## Baseline export files used actively

| File | Purpose | When used |
| ---- | ------- | --------- |
| Trade Table | Canonical transaction ledger and overlap boundary | Baseline review, overlap checks, forensic review |
| Current Balance | Asset-level checkpoint | Baseline lock, post-import verification |
| Balance by Exchange | Location-level checkpoint | Baseline lock, source-by-source verification |
| Validate Transactions | Hard structural errors flagged by CoinTracking | Before imports, after each import |
| Missing Transactions | Unmatched deposits, withdrawals, or transfers | Before imports, after each import |
| Duplicate Transactions | Duplicate gate | Before imports, after each import |
| Roll Forward in CAD | Cost and value tracing | Only when simple reports cannot explain drift |
| Double-entry | Forensic ledger detail | Only when Trade Table is not enough |
| Realized and Unrealized Gains in CAD | Sanity scan for absurd positions or results | Baseline review, final review |

## Secondary export files

| File | Keep? | Reason |
| ---- | ----- | ------ |
| Trade List | Keep, but secondary | Human-readable quick scan only |
| Coins by Exchange | Keep, but secondary | Alternative view; Balance by Exchange is primary |
| Balance By Day | Keep, but secondary | Useful only when tracking when drift begins |
| Realized Gain or Loss in CAD | Keep, but secondary | Disposal-level details when needed |
| Unrealized Gain or Loss in CAD | Keep, but secondary | Position-level details when needed |
| Average Purchase Price | Keep, but secondary | Spot-check tool only |
| Total Balance PNG | Keep, but secondary | Visual reference only |

## Files deliberately excluded from active workflow

Loose exports outside the canonical full export folder are not part of the working dataset and must not be used for decisions.

## Active helper scripts

| File | Purpose |
| ---- | ------- |
| `06_scripts/baseline_check.py` | Rebuild the durable baseline validation artifact package |
| `06_scripts/profile_source.py` | Profile raw source folders into file-family inventory and manifest-backed adapter metadata |
| `06_scripts/normalize_source.py` | Normalize raw evidence into canonical events, canonical balances, exceptions, and cached CoinTracking candidates |
| `06_scripts/normalization_common.py` | Shared canonical normalization helpers such as attached-fee behavior |
| `06_scripts/render_cointracking.py` | Render canonical events into CoinTracking CSV output with reconciliation metadata |
| `06_scripts/stage_import_batch.py` | Move only overlap-cleared candidates into the reviewed import-batch workflow |
| `06_scripts/reconcile_source.py` | Compare canonical source outputs against CoinTracking ledger slices and optional balance evidence |
| `06_scripts/pdf_balance_extract.py` | Extract deterministic balance rows from supported statement PDFs such as Coinbase Binance and Shakepay |
| `06_scripts/source_manifest.py` | Hash raw external evidence folders into deterministic manifests |
| `06_scripts/wallet_inventory.py` | Build the canonical wallet inventory plus evidence and issue artifacts from source captures |
| `06_scripts/overlap_check.py` | Screen CoinTracking-ready import batches for cutoff overlap and baseline duplicates |
| `06_scripts/round_scaffold.py` | Create a round folder and seed the round log |
| `06_scripts/verification_compare.py` | Compare two verification folders and write deterministic drift artifacts |

## Repo-local AI workflows

| Path | Purpose |
| ---- | ------- |
| `07_skills/source-intake/` | Deterministic raw-source intake, profiling, and queue-state guidance |
| `07_skills/adapter-authoring/` | Canonical adapter design, repair, and shared normalization guidance |
| `07_skills/normalization-exceptions/` | Exception-only AI workflow for unresolved normalization rows and adapter repair loops |
| `07_skills/round-verification/` | Exact post-import and post-repair verification, issue logging, and gate handling |
| `07_skills/wallet-inventory/` | Canonical wallet-identifier lookup, refresh, and issue-review workflow |
| `.claude/commands/` | Claude-compatible wrappers that expose the same workflows from a supported project-local command path |
