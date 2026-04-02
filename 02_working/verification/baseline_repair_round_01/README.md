# Verification Round

- round_id: `baseline_repair_round_01`
- phase: `baseline_repair`
- source: `Ronin - AXS Staking`

Expected default export set:

- Validate Transactions
- Missing Transactions using strict settings: `100%` amount accuracy, only `100%` matches hidden, time accuracy `-24h | +48h`
- Duplicate Transactions
- Current Balance
- Balance by Exchange

Add Trade Table, Roll Forward, or Double-entry only when needed.

Round 1 outcome:

- `Validate Transactions` cleared from 2 rows to 0 after the Ronin AXS staking repair.
- `Missing Transactions`, `Duplicate Transactions`, `Current Balance`, and `Balance by Exchange` showed no follow-on drift in the standard comparison package.

Additional forensic export:

- `CoinTracking - Missing Transactions - Strict.csv`
- Settings used: `100%` amount accuracy, only `100%` matches hidden, time accuracy `-24h | +48h`

Strict-report conclusion:

- The previously flagged `2021-05-17 20:35:21` Binance withdrawal for `803.43785040 USDT` is not the real problem transfer.
- The strict report removes that row and instead surfaces the `2021-05-17 18:57:47` Binance withdrawal for `803.58259400 USDT` together with the `2021-08-18 06:29:03` Binance return of `802.58259400 USDT`.
- Those USDT rows are now closed in the issue log as a documented returned failed-transfer event and should not trigger further CoinTracking edits.
- The strict report also surfaces an AXS withdrawal from Ronin and matching AXS deposit to Binance on `2023-02-09`; those are now tracked as `MISS-016` and `MISS-017` because the `0.00000001 AXS` fee appears to be assigned on the deposit side, which doubles the mismatch instead of netting the transfer cleanly.
