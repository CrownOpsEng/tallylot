"""CoinTracking row projection helpers."""

from __future__ import annotations

from tallylot.domain.transactions import ProjectionType, TransactionFact
from tallylot.domain.value_objects import format_decimal, format_timestamp

COINTRACKING_TYPE_LABELS = {
    ProjectionType.DEPOSIT: "Deposit",
    ProjectionType.DERIVATIVES_FUTURES_LOSS: "Derivatives / Futures Loss",
    ProjectionType.DERIVATIVES_FUTURES_PROFIT: "Derivatives / Futures Profit",
    ProjectionType.EXPENSE_NON_TAXABLE: "Expense (non taxable)",
    ProjectionType.INTEREST_INCOME: "Interest Income",
    ProjectionType.REWARD_BONUS: "Reward / Bonus",
    ProjectionType.STAKING: "Staking",
    ProjectionType.SWAP_NON_TAXABLE: "Swap (non taxable)",
    ProjectionType.TRADE: "Trade",
    ProjectionType.WITHDRAWAL: "Withdrawal",
}


def cointracking_row(transaction: TransactionFact) -> dict[str, str]:
    if not transaction.projection_type:
        raise ValueError(f"fact {transaction.fact_id} is missing CoinTracking projection metadata")
    return {
        "Type": COINTRACKING_TYPE_LABELS[transaction.projection_type],
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
