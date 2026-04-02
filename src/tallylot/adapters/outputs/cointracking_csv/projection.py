"""CoinTracking row projection helpers."""

from __future__ import annotations

from tallylot.domain.transactions import TransactionFact
from tallylot.domain.value_objects import format_decimal, format_timestamp


def cointracking_row(transaction: TransactionFact) -> dict[str, str]:
    if not transaction.projection_type:
        raise ValueError(f"fact {transaction.fact_id} is missing CoinTracking projection metadata")
    return {
        "Type": transaction.projection_type.value,
        "Buy": format_decimal(transaction.amount_in),
        "Cur.": str(transaction.asset_in or ""),
        "Sell": format_decimal(transaction.amount_out),
        "Cur..1": str(transaction.asset_out or ""),
        "Fee": format_decimal(transaction.fee_amount),
        "Cur..2": str(transaction.fee_asset or ""),
        "Exchange": transaction.account,
        "Group": transaction.operation_group_id,
        "Comment": transaction.description,
        "Date": format_timestamp(transaction.timestamp),
        "Tx-ID": transaction.tx_hash or str(transaction.fact_id),
    }
