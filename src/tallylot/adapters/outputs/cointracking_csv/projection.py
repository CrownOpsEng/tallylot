"""CoinTracking row projection helpers."""

from __future__ import annotations

from tallylot.adapters.support import is_onchain_canonical_location_id
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
    inbound_leg = _single_primary_leg(transaction, positive=True)
    outbound_leg = _single_primary_leg(transaction, positive=False)
    charge_leg = _single_charge_leg(transaction)
    _reject_other_non_primary_legs(transaction)
    return {
        "Type": COINTRACKING_TYPE_LABELS[transaction.projection_hint],
        "Buy": format_decimal(None if inbound_leg is None else inbound_leg.quantity),
        "Cur.": "" if inbound_leg is None else str(inbound_leg.instrument_id),
        "Sell": format_decimal(None if outbound_leg is None else abs(outbound_leg.quantity)),
        "Cur..1": "" if outbound_leg is None else str(outbound_leg.instrument_id),
        "Fee": format_decimal(None if charge_leg is None else abs(charge_leg.quantity)),
        "Cur..2": "" if charge_leg is None else str(charge_leg.instrument_id),
        "Exchange": _exchange_label(transaction),
        "Group": transaction.operation_group_id,
        "Comment": transaction.description,
        "Date": format_timestamp(transaction.timestamp),
        "Tx-ID": transaction.tx_hash or str(transaction.fact_id),
    }


def _single_primary_leg(transaction: TransactionFact, *, positive: bool) -> EconomicLeg | None:
    matching_legs = tuple(
        leg for leg in transaction.legs if leg.kind is LegKind.PRIMARY and (leg.quantity > 0) is positive
    )
    if len(matching_legs) > 1:
        raise ValueError(
            f"fact {transaction.fact_id} has unsupported CoinTracking projection shape: "
            f"expected at most one {'positive' if positive else 'negative'} primary leg"
        )
    return None if not matching_legs else matching_legs[0]


def _single_charge_leg(transaction: TransactionFact) -> EconomicLeg | None:
    matching_legs = tuple(leg for leg in transaction.legs if leg.kind is LegKind.CHARGE)
    if any(leg.quantity >= 0 for leg in matching_legs):
        raise ValueError(
            f"fact {transaction.fact_id} has unsupported CoinTracking projection shape: charge legs must be negative"
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


def _exchange_label(transaction: TransactionFact) -> str:
    location_id = str(transaction.location_id)
    if is_onchain_canonical_location_id(location_id):
        return str(transaction.source)
    return location_id
