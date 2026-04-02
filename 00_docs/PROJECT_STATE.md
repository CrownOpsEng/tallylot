# Project State

## Baseline checkpoint

- Canonical baseline export: `01_raw_exports/portfolio/cointracking/2023-08-05_full_export/`
- Authoritative cutoff timestamp: **2023-08-05 08:34:04**
- Delta window start: **strictly after 2023-08-05 08:34:04**
- Baseline full-export transaction count: **31,021**
- Baseline full-export duplicate report rows: **0**
- Baseline full-export validation error rows: **2**
- Baseline full-export missing transaction rows: **14**
- Baseline full-export Current Balance rows: **78**
- Baseline full-export Balance by Exchange rows: **98**

## Current verified repair status

- After `baseline_repair_round_01`, the current `Validate Transactions` export is clean at **0** rows.
- After `baseline_repair_round_02`, the current strict `Missing Transactions` export shows **2** rows.
- Those 2 rows are the already-documented Binance returned failed-transfer exception pair `MISS-013` and `MISS-015`; there are now **0** active missing-transaction issues left in `03_analysis/issues/issue_log.csv`.
- For ongoing repair and import review, `Missing Transactions` should be exported and reviewed with strict settings: **100% amount accuracy**, **only 100% matches hidden**, and **time accuracy `-24h | +48h`**.
- `MISS-013` and `MISS-015` are now closed as a documented returned failed Binance USDT transfer event that CoinTracking's missing checker cannot pair cleanly without risking a valid transfer match.
- `MISS-016` and `MISS-017` are now closed after the AXS Ronin to Binance fee-side correction cleared under strict review.
- Do not alter the valid `2021-05-17 20:35:21` Binance to Kucoin transfer to satisfy heuristic matching.

## Baseline validation status

- `Current Balance` and `Balance by Exchange` reconcile exactly at the asset-quantity level across **78** assets.
- That reconciliation is internal to CoinTracking and does not prove external wallets and exchanges were all synced to the same practical boundary.
- `03_analysis/reconciliation/baseline_source_activity.csv` now records the first and last baseline transaction timestamp seen for each source.
- The only negative balance in `Current Balance` is **CAD -15,654.23**.
- `baseline_cad_flow_by_type.csv` shows CAD bought **34,215.69**, CAD sold **49,869.92**, and CAD fees **156.26**.
- CAD deposits and withdrawals recorded in the ledger net to zero; the user manually verified that this is an intentional general CAD tracking account inside CoinTracking rather than an omitted exchange-side fiat ledger leg.
- The durable validation summary is in `00_docs/BASELINE_VALIDATION.md`.

## Universal intake capability status

- As of **2026-03-24**, deterministic universal normalization is ready for `coinbase`, `wealthsimple`, `binance`, `shakepay`, `ledger_live`, `crypto_com`, `near`, and the shared `evm_explorer` adapter on the active capture-local source folders.
- The shared `ledger_live` adapter uses the active capture label `ledger-live-main` for repo workflow and normalization output.
- The shared `near` adapter uses the active capture label `near-main` for repo workflow and normalization output.
- The shared `evm_explorer` adapter now uses chain-first workflow names such as `bsc-metamask1`, `eth-metamask1`, `polygon-metamask1`, and `eth-gala1`, each backed by a chain-scoped capture folder with a local manifest.
- The newly added Polygon token and internal-tx files closed the prior Exact Input gap, but `polygon-metamask1` still remains `needs_review`: the current raw set now reaches **2023-12-22 01:51:13** and includes five suspicious post-cutoff NFT airdrops that are intentionally held in `exceptions.csv` instead of being auto-imported as deposits.
- `eth-gala1` also remains `needs_review`: the current raw set reaches **2025-03-24 22:55:59** and includes three suspicious post-cutoff ERC-1155 NFT rows that are intentionally held in `exceptions.csv` instead of being auto-imported as deposits.
- `GTrade 1CT` remains `needs_review`: the current **2023-05-06** report is sufficient for deterministic realized PnL rows, but three open-position rows still lack the explorer or fill-level evidence needed for a CoinTracking-safe reconstruction.

## Open exception set

- `FIAT-001` is closed as a manually verified intentional general CAD tracking account unless conflicting data appears later
- `SYNC-001` is closed based on the confirmed post-baseline source list
- `VAL-001` and `VAL-002` are closed after `baseline_repair_round_01`; the current `Validate Transactions` export is clean
- All baseline missing-transaction issues are now closed in `03_analysis/issues/issue_log.csv`; the current strict report only shows the already-accepted Binance returned-transfer exception pair
- The initial post-baseline source list now starts from baseline balances above the **0.10 CAD** dust threshold; dust-only sources stay documented in the source inventory but are excluded from the initial pull queue
- Remaining open items are source-evidence and scope follow-ups rather than active baseline missing-transaction blockers

## Current decision boundary

Do **not** import any transaction after `2023-08-05 08:34:04` until:

- the issue log is updated with source proof for any newly discovered active P1 items
- the source inventory is populated for post-cutoff activity
- the next round is logged in `05_outputs/logs/round_log.csv`
