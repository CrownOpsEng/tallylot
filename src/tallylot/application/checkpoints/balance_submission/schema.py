"""User-facing schema for manual balance submissions."""

from __future__ import annotations

README_FILENAME = "README.md"
BALANCES_FILENAME = "balances.csv"
BALANCE_EVIDENCE_FILENAME = "balance_evidence.csv"
LOCATION_INVENTORY_FILENAME = "location_inventory.csv"
BALANCES_EXAMPLE_FILENAME = f"{BALANCES_FILENAME}.example"
BALANCE_EVIDENCE_EXAMPLE_FILENAME = f"{BALANCE_EVIDENCE_FILENAME}.example"
LOCATION_INVENTORY_EXAMPLE_FILENAME = f"{LOCATION_INVENTORY_FILENAME}.example"
SUMMARY_FILENAME = "balance_submission_summary.json"
ISSUES_FILENAME = "balance_submission_issues.csv"
MANUAL_SUBMISSION_EVIDENCE_KIND = "manual_submission"

BALANCES_HEADER = (
    "source",
    "account",
    "wallet",
    "instrument_id",
    "quantity",
    "as_of_at",
    "as_of_precision",
    "balance_kind",
    "notes",
)
BALANCE_EVIDENCE_HEADER = (
    "source",
    "account",
    "wallet",
    "instrument_id",
    "quantity",
    "as_of_at",
    "as_of_precision",
    "balance_kind",
    "evidence_ref",
    "notes",
)
LOCATION_INVENTORY_HEADER = (
    "source",
    "account",
    "wallet",
    "identifier_kind",
    "identifier_value",
    "network_scope",
    "controller",
    "confidence",
    "notes",
)
ISSUE_HEADER = (
    "file_name",
    "row_number",
    "column_name",
    "issue_kind",
    "message",
)
