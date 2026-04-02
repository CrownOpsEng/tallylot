"""Application-owned balance derivation from facts."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal

from tallylot.domain.checkpoints import BalanceSnapshot
from tallylot.domain.transactions import TransactionFact
from tallylot.domain.types import AssetSymbol, LocationId, SourceId


def derive_balance_snapshots(
    facts: tuple[TransactionFact, ...],
) -> tuple[BalanceSnapshot, ...]:
    balances: dict[tuple[str, str, str], Decimal] = defaultdict(lambda: Decimal("0"))
    latest_timestamp: datetime | None = None
    for fact in facts:
        latest_timestamp = fact.timestamp if latest_timestamp is None else max(latest_timestamp, fact.timestamp)
        for leg in fact.legs:
            _apply_balance_delta(
                balances,
                key=(
                    str(fact.source),
                    str(leg.location_id or fact.location_id),
                    str(leg.asset),
                ),
                quantity=leg.amount if leg.direction == "in" else -leg.amount,
            )
    as_of = latest_timestamp if latest_timestamp is not None else datetime.now(UTC)
    return tuple(
        BalanceSnapshot(
            source=SourceId(source),
            location_id=LocationId(location_id),
            asset=AssetSymbol(asset),
            quantity=quantity,
            as_of=as_of,
        )
        for (source, location_id, asset), quantity in sorted(balances.items())
    )


def _apply_balance_delta(
    balances: dict[tuple[str, str, str], Decimal],
    *,
    key: tuple[str, str, str],
    quantity: Decimal,
) -> None:
    balances[key] += quantity
