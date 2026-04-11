"""Balance target planning helpers."""

from __future__ import annotations

from datetime import UTC, datetime

from tallylot.domain.balances import BalanceTarget
from tallylot.domain.instruments import InstrumentId
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.transactions import TransactionFact
from tallylot.domain.types import LocationId, SourceId


def latest_balance_targets(
    facts: tuple[TransactionFact, ...],
) -> tuple[BalanceTarget, ...]:
    latest_by_key: dict[tuple[str, str, str, str], datetime] = {}
    for fact in facts:
        for leg in fact.legs:
            key = (
                str(fact.source),
                str(leg.location_id or fact.location_id),
                str(leg.instrument_id),
                "available",
            )
            current = latest_by_key.get(key)
            latest_by_key[key] = (
                fact.timestamp if current is None else max(current, fact.timestamp)
            )
    return tuple(
        BalanceTarget(
            source=SourceId(source),
            location_id=LocationId(location_id),
            instrument_id=InstrumentId(instrument_id),
            balance_kind=balance_kind,
            target_at=latest_by_key[(source, location_id, instrument_id, balance_kind)],
            target_precision=TemporalPrecision.TIMESTAMP,
        )
        for source, location_id, instrument_id, balance_kind in sorted(latest_by_key)
    )


def targets_for_as_of_values(
    facts: tuple[TransactionFact, ...],
    requested_times: tuple[tuple[datetime, TemporalPrecision], ...],
) -> tuple[BalanceTarget, ...]:
    keys: set[tuple[str, str, str, str]] = set()
    for fact in facts:
        for leg in fact.legs:
            keys.add(
                (
                    str(fact.source),
                    str(leg.location_id or fact.location_id),
                    str(leg.instrument_id),
                    "available",
                )
            )
    targets: list[BalanceTarget] = []
    for source, location_id, instrument_id, balance_kind in sorted(keys):
        for target_at, target_precision in requested_times:
            targets.append(
                BalanceTarget(
                    source=SourceId(source),
                    location_id=LocationId(location_id),
                    instrument_id=InstrumentId(instrument_id),
                    balance_kind=balance_kind,
                    target_at=target_at,
                    target_precision=target_precision,
                )
            )
    return tuple(targets)


def parse_target_time_values(
    values: tuple[str, ...],
) -> tuple[tuple[datetime, TemporalPrecision], ...]:
    if not values:
        return ()
    parsed: list[tuple[datetime, TemporalPrecision]] = []
    for value in values:
        text = value.strip()
        if not text:
            raise ValueError("balance target times must not be blank")
        if " " in text:
            parsed.append(
                (
                    datetime.strptime(text, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC),
                    TemporalPrecision.TIMESTAMP,
                )
            )
            continue
        parsed.append(
            (
                datetime.strptime(text, "%Y-%m-%d").replace(tzinfo=UTC),
                TemporalPrecision.DATE,
            )
        )
    return tuple(parsed)
