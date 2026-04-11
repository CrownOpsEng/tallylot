"""Balance target planning helpers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

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
    *,
    timezone_value: str = "",
) -> tuple[tuple[datetime, TemporalPrecision], ...]:
    if not values:
        return ()
    default_timezone = _parse_timezone_value(timezone_value)
    parsed: list[tuple[datetime, TemporalPrecision]] = []
    for value in values:
        text = value.strip()
        if not text:
            raise ValueError("balance target times must not be blank")
        if _looks_like_date_only(text):
            naive_date = datetime.strptime(text, "%Y-%m-%d")
            parsed.append(
                (
                    naive_date.replace(tzinfo=default_timezone).astimezone(UTC),
                    TemporalPrecision.TIMESTAMP,
                )
            )
            continue
        parsed.append(
            (
                _parse_timestamp_value(text, default_timezone),
                TemporalPrecision.TIMESTAMP,
            )
        )
    return tuple(parsed)


def _looks_like_date_only(value: str) -> bool:
    return len(value) == 10 and value[4] == "-" and value[7] == "-"


def _parse_timestamp_value(value: str, default_timezone: tzinfo) -> datetime:
    normalized = value.replace("T", " ").replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"invalid balance target time: {value}") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        parsed = parsed.replace(tzinfo=default_timezone)
    return parsed.astimezone(UTC)


def _parse_timezone_value(value: str) -> tzinfo:
    text = value.strip()
    if not text or text.upper() == "UTC":
        return UTC
    if text.startswith(("UTC+", "UTC-")):
        return _fixed_offset_timezone(text[3:])
    if text.startswith(("+", "-")):
        return _fixed_offset_timezone(text)
    try:
        return ZoneInfo(text)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"unknown timezone: {value}") from exc


def _fixed_offset_timezone(value: str) -> timezone:
    sign = -1 if value.startswith("-") else 1
    hours_text, separator, minutes_text = value[1:].partition(":")
    if not hours_text or (separator and not minutes_text):
        raise ValueError(f"unknown timezone: UTC{value}")
    try:
        hours = int(hours_text)
        minutes = int(minutes_text or "0")
    except ValueError as exc:
        raise ValueError(f"unknown timezone: UTC{value}") from exc
    return timezone(sign * timedelta(hours=hours, minutes=minutes))
