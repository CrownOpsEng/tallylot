"""Application-owned balance derivation from facts."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal

from tallylot.domain.checkpoints import BalanceSnapshot
from tallylot.domain.instruments import InstrumentId
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.transactions import TransactionFact
from tallylot.domain.types import LocationId, SourceId


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
                    str(leg.instrument_id),
                ),
                quantity=leg.quantity,
            )
    as_of = latest_timestamp if latest_timestamp is not None else datetime.now(UTC)
    return tuple(
        BalanceSnapshot(
            source=SourceId(source),
            location_id=LocationId(location_id),
            instrument_id=InstrumentId(instrument_id),
            quantity=quantity,
            as_of_at=as_of,
            as_of_precision=TemporalPrecision.TIMESTAMP,
        )
        for (source, location_id, instrument_id), quantity in sorted(balances.items())
    )


def _apply_balance_delta(
    balances: dict[tuple[str, str, str], Decimal],
    *,
    key: tuple[str, str, str],
    quantity: Decimal,
) -> None:
    balances[key] += quantity
