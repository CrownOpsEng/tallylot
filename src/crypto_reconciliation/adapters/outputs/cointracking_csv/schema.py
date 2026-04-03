"""CoinTracking CSV schema definitions."""

from __future__ import annotations

COINTRACKING_HEADER = (
    "Type",
    "Buy",
    "Cur.",
    "Sell",
    "Cur..1",
    "Fee",
    "Cur..2",
    "Exchange",
    "Group",
    "Comment",
    "Date",
    "Tx-ID",
)

CANDIDATE_ARTIFACT_NAME = "cointracking_candidate.csv"

REQUIRED_BASELINE_EXPORTS = (
    "Trade Table",
    "Current Balance",
    "Balance by Exchange",
    "Validate Transactions",
    "Missing Transactions",
    "Duplicate Transactions",
)
