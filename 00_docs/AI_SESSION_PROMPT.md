# AI Session Working Prompt

Use CoinTracking.info as the live ledger and this repo as the evidence and verification workspace.

Always anchor to these facts first:

1. canonical baseline folder: `01_raw_exports/portfolio/cointracking/2023-08-05_full_export/`
2. authoritative cutoff timestamp: `2023-08-05 08:34:04`
3. delta work begins strictly after that timestamp unless a newer baseline is intentionally adopted

Source order for analysis:

1. canonical baseline exports in `01_raw_exports/portfolio/cointracking/2023-08-05_full_export/`
2. CRA-aligned tax guidance in `00_docs/CANADIAN_CRYPTOCURRENCY_TAXATION_GUIDE.md`
3. targeted CRA source lookup via `00_docs/TAX_REFERENCE_MAP.md` when the guide is not enough
4. durable baseline validation in `00_docs/BASELINE_VALIDATION.md`
5. fresh verification exports in `02_working/verification/`
6. raw external source exports in `01_raw_exports/source/`
7. working derivatives in `02_working/`

Operational rules:

1. consult `03_analysis/issues/issue_log.csv` for unresolved items
2. consult `03_analysis/issues/source_inventory.csv` before any new source planning
3. follow CRA primary guidance when tax treatment questions arise; use `00_docs/TAX_REFERENCE_MAP.md` to jump to the smallest relevant source
4. treat `FIAT-001` as closed unless conflicting evidence appears later; the current documented position is that it is an intentional general CAD tracking account
5. update `03_analysis/issues/issue_log.csv` when new evidence, actions, or outcomes appear
6. update `05_outputs/logs/round_log.csv` after each repair or import round
7. request only the default verification export set unless a mismatch requires a heavier report
8. never recommend importing the next source until the current one passes verification

Default verification exports to request after any repair or import:

- Validate Transactions
- Missing Transactions using strict settings: `100%` amount accuracy, only `100%` matches hidden, time accuracy `-24h | +48h`
- Duplicate Transactions
- Current Balance
- Balance by Exchange
