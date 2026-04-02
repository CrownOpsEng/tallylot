# Issues And Inventory Guide

This folder holds the two live issue-tracking control files that must stay
current during execution.

Related generated inventory artifacts now live beside them in
`analysis/inventory/`, especially `wallet_inventory.csv` and
`wallet_inventory_issues.csv`.

## `issue_log.csv`

Use this file for baseline exceptions and any new issues discovered during repair or import rounds.

`issue_id` is a controlled namespace. Only these prefixes are allowed:

- `MISS-###` → Missing Transactions and Missing Transactions - Strict issues
- `VAL-###` → Validate Transactions issues
- `BAL-###` → balance investigations where the mismatch is visible but the origin is not yet proven, including per-source ending-balance gaps and residual-balance reviews
- `SRC-###` → source-scoped issues of any kind, including raw export gaps, source evidence gaps, source scope questions, and source-specific transaction-backing or classification reviews
- `SYNC-###` → ledger-wide boundary and synchronization issues
- `FIAT-###` → ledger-wide fiat-layer issues

Do not invent exchange-specific prefixes such as `CB-` or `BIN-`.
Use the `exchange`, `source_file`, and `issue_class` columns to express which source is involved.
If an old issue family needs a new row, continue numbering inside the existing allowed prefix rather than creating a new namespace.

Numbering policy:

- `issue_log.csv` is append-only. Add new issues at the end and update existing rows in place.
- Within each allowed prefix family, assign the next number as `max(existing) + 1`.
- Never renumber existing rows just to tidy the file.
- Never reuse skipped or retired numbers. Gaps are allowed and may reflect deleted or superseded rows.
- If an issue is reclassified but stays in the same family, keep the existing row and update its fields in place.
- If an issue is reclassified into a different allowed family, keep the row in place but assign the next append-only number in the new family and update references.

Key fields:

- `proof_path` → exact raw file, explorer record, or evidence location used to justify a decision
- `proof_summary` → short explanation of what the proof establishes
- `external_action` → exact manual change made in the current external
  verification or tracker tool
- `verification_path` → round folder containing the fresh post-change exports
- `gate_result` → outcome after reviewing the fresh exports

Suggested `gate_result` values:

- `blocked_pending_evidence`
- `pending_review`
- `passed`
- `failed_needs_repair`
- `accepted_exception`

`FIAT-001` is the baseline fiat-layer completeness issue. Keep it open until
the CAD funding and withdrawal chain is either repaired in the current
external verification tool or explicitly documented with supporting evidence.

Prefix guidance:

- Coinbase-specific issues belong under `SRC-*`, not a Coinbase-only prefix.
- Binance-specific issues belong under `SRC-*` unless they are literally a Missing Transactions or Validate Transactions issue, in which case they stay under `MISS-*` or `VAL-*`.
- Balance mismatches or residual balances that are visible in source or tracker
  reports but do not yet prove where the error originates belong under
  `BAL-*`, not `SRC-*`.
- Prefixes classify workflow family, not exchange.

## `source_inventory.csv`

Use this file to track every source that may have activity after the baseline cutoff.

Update the row continuously as facts are confirmed:

- when activity is confirmed or excluded
- when the capture folder and manifest are present
- when the import batch is overlap-screened and ready
- when the source is imported and then fully verified

Suggested `status` values:

- `needs_user_confirmation` → source is known from the baseline, but post-cutoff activity is not yet confirmed
- `pending_inventory_confirmation` → source is expected to be active, but timing or scope still needs confirmation
- `confirmed_active_pending_export` → post-cutoff activity is confirmed and the source is in scope, but capture files have not been pulled yet
- `capture_complete` → the capture folder and manifest are present
- `ready_for_import` → cleaned import file is prepared and overlap-screened
- `imported_pending_verification` → source was imported into the current
  tracker workflow and fresh exports still need review
- `complete` → source import is verified and closed
- `excluded_no_activity` → confirmed no post-cutoff activity
- `excluded_dust_balance` → confirmed post-cutoff activity exists, but the source is excluded from the initial queue because its baseline balance is within the agreed dust threshold

Keep the values consistent so AI and manual review can sort and filter reliably.
