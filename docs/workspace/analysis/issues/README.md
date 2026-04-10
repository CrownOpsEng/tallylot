---
title: "Issues And Inventory Guide"
summary: "Rules for the live issue and source inventory control files in the mirrored workspace."
doc_type: reference
audience: both
owner: repo
status: active
---

This folder holds the live issue, inventory, and intake-control files that
must stay current during execution.

Related generated inventory artifacts now live beside them in
`analysis/inventory/`, especially `source_captures.csv`,
`location_inventory.csv`, and `location_inventory_issues.csv`.

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
- `external_action` → exact manual change made in the external verification tool
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
- Balance mismatches or residual balances that are visible in source or external verification
  reports but do not yet prove where the error originates belong under
  `BAL-*`, not `SRC-*`.
- Prefixes classify workflow family, not exchange.

## `source_inventory.csv`

Use this file for source-summary state only.

Update the row continuously as source scope and assembly state become clearer:

- when activity is confirmed or excluded
- when capture counts and latest accepted captures change
- when assembly is blocked, pending, or complete
- when the external import and verification workflow advances

This file does not store one source-level `capture_path`. Capture detail belongs
in `analysis/inventory/source_captures.csv`.

Suggested `status` values:

These values describe the current external import and verification workflow.

- `needs_user_confirmation` → source is known from the baseline, but post-cutoff activity is not yet confirmed
- `pending_inventory_confirmation` → source is expected to be active, but timing or scope still needs confirmation
- `confirmed_active_pending_export` → post-cutoff activity is confirmed and the source is in scope, but capture files have not been pulled yet
- `capture_complete` → the capture folder and manifest are present
- `ready_for_import` → cleaned import file is prepared and overlap-screened
- `imported_pending_verification` → source was imported into the current
  external verification workflow and fresh exports still need review
- `complete` → source import is verified and closed
- `excluded_no_activity` → confirmed no post-cutoff activity
- `excluded_dust_balance` → confirmed post-cutoff activity exists, but the source is excluded from the initial queue because its baseline balance is within the agreed dust threshold

Keep the values consistent so AI and manual review can sort and filter reliably.

## `analysis/inventory/source_captures.csv`

Use this append-only registry to track each intake capture for a source.

Rules:

- `capture_uid` is the immutable canonical capture identity
- `capture_label` is the human-readable raw folder name
- `capture_root_ref` is workspace-relative
- `supersedes_capture_uid` is explicit when one capture replaces another
- status captures intake, review, normalization, and assembly progression

## `source_label_map.csv`

Use this file when intake should preserve a stable operator-managed source
label instead of landing files under a generated or content-derived label.

Each row maps an incoming path prefix to a source label that already exists in
`source_inventory.csv`.

Rules:

- `incoming_path_prefix` is relative to the intake `--incoming-dir`
- `.` applies to the entire incoming capture
- keep prefixes durable and operator-meaningful rather than adapter-specific
- use the file when raw source evidence or source-scoped working artifacts
  should stay associated with an existing stable source label
- do not use this file to invent new source labels implicitly; add the source
  to `source_inventory.csv` first

Intake plan and apply both read this file from the workspace root. When a valid
map row matches, it overrides content-based source-folder generation. When a
matching row is invalid or points at an unknown source, intake surfaces that as
an explicit plan/apply issue and skips the affected rows instead of silently
falling back.
