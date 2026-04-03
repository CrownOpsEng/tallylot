"""Shared staging constants."""

from __future__ import annotations

NORMALIZED_TIMEZONE = "UTC"
OUTPUT_IMPORT_TIMEZONE = "UTC"
ISSUE_HEADER = (
    "issue_id",
    "source",
    "adapter_id",
    "severity",
    "kind",
    "message",
    "context_timestamp",
    "raw_file",
    "raw_row_ref",
    "status",
)
OVERLAP_FLAGGED_HEADER = (
    "row_number",
    "reasons",
    "type",
    "buy",
    "buy_currency",
    "sell",
    "sell_currency",
    "fee",
    "fee_currency",
    "exchange",
    "date",
    "tx_id",
)
