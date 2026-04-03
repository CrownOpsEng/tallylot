"""Structured CSV adapter-local contracts."""

from __future__ import annotations

from dataclasses import dataclass

TRANSACTIONS_FILENAME = "transactions.csv"

REQUIRED_HEADER = (
    "timestamp",
    "category",
    "asset_in",
    "amount_in",
    "asset_out",
    "amount_out",
    "fee_asset",
    "fee_amount",
    "tx_hash",
    "description",
    "account",
    "wallet",
)


@dataclass(frozen=True)
class ReviewValues:
    field_name: str = ""
    original_value: str = ""
    normalized_value: str = ""


EMPTY_REVIEW_VALUES = ReviewValues()


@dataclass(frozen=True)
class ReviewSpec:
    kind: str
    message: str
    values: ReviewValues = EMPTY_REVIEW_VALUES
