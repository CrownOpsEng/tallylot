"""CoinTracking row projection helpers."""

from __future__ import annotations

from tallylot.domain.transactions import EconomicLeg, LegKind, ProjectionHint, TransactionFact
from tallylot.domain.value_objects import format_decimal, format_timestamp

COINTRACKING_TYPE_LABELS = {
    ProjectionHint.DEPOSIT: "Deposit",
    ProjectionHint.DERIVATIVES_FUTURES_LOSS: "Derivatives / Futures Loss",
    ProjectionHint.DERIVATIVES_FUTURES_PROFIT: "Derivatives / Futures Profit",
    ProjectionHint.EXPENSE_NON_TAXABLE: "Expense (non taxable)",
    ProjectionHint.INTEREST_INCOME: "Interest Income",
    ProjectionHint.REWARD_BONUS: "Reward / Bonus",
    ProjectionHint.STAKING: "Staking",
    ProjectionHint.SWAP_NON_TAXABLE: "Swap (non taxable)",
    ProjectionHint.TRADE: "Trade",
    ProjectionHint.WITHDRAWAL: "Withdrawal",
}


def cointracking_row(transaction: TransactionFact) -> dict[str, str]:
    if not transaction.projection_hint:
        raise ValueError(f"fact {transaction.fact_id} is missing CoinTracking projection metadata")
    if not any(leg.kind is LegKind.PRIMARY for leg in transaction.legs):
        raise ValueError(
            f"fact {transaction.fact_id} has unsupported CoinTracking projection shape: "
            "expected at least one primary leg"
        )
    inbound_leg = _single_primary_leg(transaction, direction="in")
    outbound_leg = _single_primary_leg(transaction, direction="out")
    charge_leg = _single_charge_leg(transaction)
    _reject_other_non_primary_legs(transaction)
    return {
        "Type": COINTRACKING_TYPE_LABELS[transaction.projection_hint],
        "Buy": format_decimal(None if inbound_leg is None else inbound_leg.amount),
        "Cur.": "" if inbound_leg is None else str(inbound_leg.asset),
        "Sell": format_decimal(None if outbound_leg is None else outbound_leg.amount),
        "Cur..1": "" if outbound_leg is None else str(outbound_leg.asset),
        "Fee": format_decimal(None if charge_leg is None else charge_leg.amount),
        "Cur..2": "" if charge_leg is None else str(charge_leg.asset),
        "Exchange": str(transaction.location_id),
        "Group": transaction.operation_group_id,
        "Comment": transaction.description,
        "Date": format_timestamp(transaction.timestamp),
        "Tx-ID": transaction.tx_hash or str(transaction.fact_id),
    }


def _single_primary_leg(transaction: TransactionFact, *, direction: str) -> EconomicLeg | None:
    matching_legs = tuple(leg for leg in transaction.legs if leg.kind is LegKind.PRIMARY and leg.direction == direction)
    if len(matching_legs) > 1:
        raise ValueError(
            f"fact {transaction.fact_id} has unsupported CoinTracking projection shape: "
            f"expected at most one {direction}bound primary leg"
        )
    return None if not matching_legs else matching_legs[0]


def _single_charge_leg(transaction: TransactionFact) -> EconomicLeg | None:
    matching_legs = tuple(leg for leg in transaction.legs if leg.kind is LegKind.CHARGE)
    if any(leg.direction != "out" for leg in matching_legs):
        raise ValueError(
            f"fact {transaction.fact_id} has unsupported CoinTracking projection shape: charge legs must be outbound"
        )
    if len(matching_legs) > 1:
        raise ValueError(
            f"fact {transaction.fact_id} has unsupported CoinTracking projection shape: expected at most one charge leg"
        )
    return None if not matching_legs else matching_legs[0]


def _reject_other_non_primary_legs(transaction: TransactionFact) -> None:
    unsupported_kinds = sorted(
        {leg.kind.value for leg in transaction.legs if leg.kind not in {LegKind.PRIMARY, LegKind.CHARGE}}
    )
    if unsupported_kinds:
        raise ValueError(
            f"fact {transaction.fact_id} has unsupported CoinTracking projection leg kinds: "
            f"{', '.join(unsupported_kinds)}"
        )
