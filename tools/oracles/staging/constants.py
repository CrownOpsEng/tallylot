"""Shared staging constants."""

from __future__ import annotations

NORMALIZED_TIMEZONE = "UTC"
OUTPUT_IMPORT_TIMEZONE = "UTC"
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
