"""Application-owned balance derivation from facts."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal

from tallylot.domain.checkpoints import BalanceSnapshot
from tallylot.domain.transactions import TransactionFact
from tallylot.domain.types import AssetSymbol, SourceId


def derive_balance_snapshots(
    facts: tuple[TransactionFact, ...],
) -> tuple[BalanceSnapshot, ...]:
    balances: dict[tuple[str, str, str, str], Decimal] = defaultdict(lambda: Decimal("0"))
    latest_timestamp: datetime | None = None
    for fact in facts:
        latest_timestamp = fact.timestamp if latest_timestamp is None else max(latest_timestamp, fact.timestamp)
        if fact.asset_in is not None and fact.amount_in is not None:
            _apply_balance_delta(
                balances,
                key=(
                    str(fact.source),
                    fact.account,
                    fact.wallet,
                    str(fact.asset_in),
                ),
                quantity=fact.amount_in,
            )
        if fact.asset_out is not None and fact.amount_out is not None:
            _apply_balance_delta(
                balances,
                key=(
                    str(fact.source),
                    fact.account,
                    fact.wallet,
                    str(fact.asset_out),
                ),
                quantity=-fact.amount_out,
            )
        if fact.fee_asset is not None and fact.fee_amount is not None:
            _apply_balance_delta(
                balances,
                key=(
                    str(fact.source),
                    fact.account,
                    fact.wallet,
                    str(fact.fee_asset),
                ),
                quantity=-fact.fee_amount,
            )
    as_of = latest_timestamp if latest_timestamp is not None else datetime.now(UTC)
    return tuple(
        BalanceSnapshot(
            source=SourceId(source),
            account=account,
            wallet=wallet,
            asset=AssetSymbol(asset),
            quantity=quantity,
            as_of=as_of,
        )
        for (source, account, wallet, asset), quantity in sorted(balances.items())
    )


def _apply_balance_delta(
    balances: dict[tuple[str, str, str, str], Decimal],
    *,
    key: tuple[str, str, str, str],
    quantity: Decimal,
) -> None:
    balances[key] += quantity
