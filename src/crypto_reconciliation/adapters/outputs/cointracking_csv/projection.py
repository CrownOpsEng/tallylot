"""CoinTracking row projection helpers."""

from __future__ import annotations

from crypto_reconciliation.domain.models import NormalizedTransaction
from crypto_reconciliation.domain.value_objects import format_decimal, format_timestamp


def cointracking_row(transaction: NormalizedTransaction) -> dict[str, str]:
    if not transaction.projection_type:
        raise ValueError(f"transaction {transaction.transaction_id} is missing CoinTracking projection metadata")
    return {
        "Type": transaction.projection_type,
        "Buy": format_decimal(transaction.amount_in),
        "Cur.": str(transaction.asset_in or ""),
        "Sell": format_decimal(transaction.amount_out),
        "Cur..1": str(transaction.asset_out or ""),
        "Fee": format_decimal(transaction.fee_amount),
        "Cur..2": str(transaction.fee_asset or ""),
        "Exchange": transaction.account,
        "Group": transaction.group_key,
        "Comment": transaction.description,
        "Date": format_timestamp(transaction.timestamp),
        "Tx-ID": transaction.tx_hash or str(transaction.transaction_id),
    }
