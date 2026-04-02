# Timezone Validation

As of 2026-03-24, the intake pipeline normalizes all canonical timestamps to `UTC` and now records per-file timezone provenance before normalization. This document ties each implemented source family to the platform export capability that exists today, the timezone evidence actually present in the exported files, and the guardrails now enforced in code.

## Source Matrix

| Source family | Platform export capability | Timezone evidence used in this repo | Pipeline policy | Status |
| ---- | ---- | ---- | ---- | ---- |
| Coinbase | Coinbase Exchange exposes Accounts, Fills, and Balance statements: <https://help.coinbase.com/en/exchange/managing-my-account/account-history-and-reports> | Retail CSV timestamps include `UTC`; Coinbase Pro fills/statements use ISO timestamps ending in `Z`; Coinbase Commerce docs also describe report times as UTC: <https://help.coinbase.com/en/commerce/managing-account/transaction-reporting> | Require explicit UTC in header or value | Document-backed |
| Wealthsimple | Wealthsimple documents `Activities export (CSV)` for Crypto accounts: <https://help.wealthsimple.com/hc/en-ca/articles/35654428540571-Request-a-custom-statement> | Current `activities-export` files are date-only (`transaction_date`, optional `settlement_date`) with no time-of-day or timezone column | Treat as date-only evidence and use full-day reconciliation tolerance | Capability doc found; timezone inferred from raw export |
| Binance | Binance publishes account-history API families and downloadable history endpoints in official docs, including deposit history and futures trade-history download APIs: <https://www.binance.com/en/skills/detail/binance/assets>, <https://www.binance.com/en/skills/detail/binance/derivatives-trading-usds-futures> | Current exports either embed an offset in the filename like `(UTC--6)` or expose `UTC_Time` in the CSV header | Require filename offset or explicit UTC header; reject naive timed rows | Capability doc found; UI export timezone inferred from raw export |
| Crypto.com | Crypto.com App supports CSV exports for Crypto Wallet and Cash Wallet histories: <https://help.crypto.com/en/articles/3438579-how-do-i-export-my-transaction-history-app> | Current CSVs use `Timestamp (UTC)` | Require explicit UTC in header or value | Document-backed |
| Shakepay | Shakepay provides downloadable transaction-history CSVs and reports: <https://help.shakepay.com/en/articles/3336094-where-to-find-my-shakepay-reports> | Current cash and crypto CSVs are naive local timestamps with no UTC marker | Interpret as source-local `America/Toronto`; reject conflicting markers | Capability doc found; timezone inferred from raw export and preserved as an explicit adapter policy |
| MetaMask / EVM explorer | MetaMask directs users to network block explorers for transaction history: <https://support.metamask.io/es/start/how-do-i-find-my-transactions/> | Explorer CSVs used in this repo expose `DateTime (UTC)` | Require explicit UTC in header or value | Document-backed through explorer workflow plus raw export headers |
| Ledger Live | No stable official Ledger help article documenting CSV export timezone semantics was located during this review | Current `ledgerlive-operations-*.csv` rows use ISO timestamps ending in `Z` | Require explicit UTC in value | Raw-export evidence-backed |
| NEAR / NearBlocks | NearBlocks account pages expose `CSV Export`: <https://nearblocks.io/address/official-near.near> | Current exported CSVs use a naive `Time` column with no explicit timezone marker | Interpret as UTC for the current NearBlocks export family; reject conflicting markers if the export format changes | Capability doc found; timezone inferred from raw export family |
| GTrade | No current official platform documentation for report-export timezone semantics was located during this review | Current report CSV exposes only `DATE` values | Treat as date-only evidence and use full-day reconciliation tolerance | Raw-export evidence-backed |

## Automatic Controls

The pipeline now enforces these controls:

1. `profile_source.py` records timezone provenance for every dated CSV row in `profile_inventory.csv`:
   `timestamp_resolution`, `timezone_mode`, `timezone_value`, `timezone_conflict`
2. `profile_source.py` also writes `timezone_issues.csv` plus `timezone_summary` in `profile.json`.
3. `normalize_source.py` runs adapter-specific timezone validation before normalization and refuses to continue when timezone issues exist.
4. Empty placeholder exports such as Binance `No data matches the criteria.` files are ignored instead of being misclassified as timezone failures.
5. Date-only sources currently covered by this repo, Wealthsimple and GTrade, now render with `render_match_window_seconds=86399` so reconciliation does not pretend they carry exact-second evidence.

## Accepted Timezone Modes

The validation layer classifies dated files into these modes:

| Mode | Meaning |
| ---- | ------- |
| `header_utc` | The CSV header explicitly declares UTC, for example `Timestamp (UTC)` or `DateTime (UTC)` |
| `value_utc` | The timestamp value itself declares UTC, for example `... UTC` or `...Z` |
| `filename_offset` | The export filename carries the timezone offset used when the report was generated |
| `date_only` | The source provides only a calendar date, not a time-of-day |
| `naive` | The source provides a time-of-day without a timezone marker |
| `conflict` | The file exposes contradictory timezone hints and must be reviewed before use |

## Operating Rule

If a source format changes and its timezone provenance no longer matches the expected adapter policy, stop at profiling, review `timezone_issues.csv`, and do not stage or import that source until the policy is repaired with evidence.
