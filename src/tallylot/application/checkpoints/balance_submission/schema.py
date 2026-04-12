"""User-facing schema for manual balance submissions."""

from __future__ import annotations

from tallylot.application.balances import (
    BALANCE_REFERENCE_FILENAME,
    BALANCE_SNAPSHOT_FILENAME,
)

README_FILENAME = "README.md"
BALANCE_SNAPSHOTS_FILENAME = BALANCE_SNAPSHOT_FILENAME
BALANCE_REFERENCES_FILENAME = BALANCE_REFERENCE_FILENAME
LOCATION_INVENTORY_FILENAME = "location_inventory.csv"
BALANCE_SNAPSHOTS_EXAMPLE_FILENAME = f"{BALANCE_SNAPSHOTS_FILENAME}.example"
BALANCE_REFERENCES_EXAMPLE_FILENAME = f"{BALANCE_REFERENCES_FILENAME}.example"
LOCATION_INVENTORY_EXAMPLE_FILENAME = f"{LOCATION_INVENTORY_FILENAME}.example"
SUMMARY_FILENAME = "balance_submission_summary.json"
ISSUES_FILENAME = "balance_submission_issues.csv"
MANUAL_SUBMISSION_EVIDENCE_KIND = "manual_submission"

BALANCE_SNAPSHOTS_HEADER = (
    "source",
    "account",
    "wallet",
    "instrument_id",
    "quantity",
    "target_at",
    "target_precision",
    "balance_kind",
    "notes",
)
BALANCE_REFERENCES_HEADER = (
    "source",
    "account",
    "wallet",
    "instrument_id",
    "quantity",
    "target_at",
    "target_precision",
    "balance_kind",
    "reference_kind",
    "observed_at",
    "observed_precision",
    "support_ref",
    "reviewed_by",
    "reviewed_at",
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
