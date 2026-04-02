"""CoinTracking row projection helpers."""

from __future__ import annotations

from tallylot.domain.transactions import EconomicLeg, ProjectionType, TransactionFact
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
    inbound_leg = _single_leg(transaction, direction="in")
    outbound_leg = _single_leg(transaction, direction="out")
    fee_leg = _single_fee_leg(transaction)
    return {
        "Type": COINTRACKING_TYPE_LABELS[transaction.projection_type],
        "Buy": format_decimal(None if inbound_leg is None else inbound_leg.amount),
        "Cur.": "" if inbound_leg is None else str(inbound_leg.asset),
        "Sell": format_decimal(None if outbound_leg is None else outbound_leg.amount),
        "Cur..1": "" if outbound_leg is None else str(outbound_leg.asset),
        "Fee": format_decimal(None if fee_leg is None else fee_leg.amount),
        "Cur..2": "" if fee_leg is None else str(fee_leg.asset),
        "Exchange": transaction.account,
        "Group": transaction.operation_group_id,
        "Comment": transaction.description,
        "Date": format_timestamp(transaction.timestamp),
        "Tx-ID": transaction.tx_hash or str(transaction.fact_id),
    }


def _single_leg(transaction: TransactionFact, *, direction: str) -> EconomicLeg | None:
    matching_legs = tuple(leg for leg in transaction.legs if leg.direction == direction)
    if len(matching_legs) > 1:
        raise ValueError(
            f"fact {transaction.fact_id} has unsupported CoinTracking projection shape: "
            f"expected at most one {direction}bound leg"
        )
    return None if not matching_legs else matching_legs[0]


def _single_fee_leg(transaction: TransactionFact) -> EconomicLeg | None:
    if len(transaction.fee_legs) > 1:
        raise ValueError(
            f"fact {transaction.fact_id} has unsupported CoinTracking projection shape: expected at most one fee leg"
        )
    return None if not transaction.fee_legs else transaction.fee_legs[0]
