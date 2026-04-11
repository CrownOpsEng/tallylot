"""Filesystem balance row decoding helpers."""

from __future__ import annotations

from tallylot.domain.balances import (
    BalanceReference,
    BalanceReferenceKind,
    BalanceSnapshot,
    BalanceTarget,
    normalize_balance_kind,
)
from tallylot.domain.instruments import InstrumentId
from tallylot.domain.temporal import parse_temporal_precision
from tallylot.domain.types import LocationId, SourceId
from tallylot.domain.value_objects import (
    parse_decimal,
    parse_temporal_value,
    parse_timestamp,
)


def balance_snapshot_from_row(row: dict[str, str]) -> BalanceSnapshot:
    precision = parse_temporal_precision(row["target_precision"])
    if precision is None:
        raise ValueError("missing required enum field: target_precision")
    quantity = parse_decimal(row["quantity"])
    if quantity is None:
        raise ValueError("missing required decimal field: quantity")
    return BalanceSnapshot(
        target=BalanceTarget(
            source=SourceId(row["source"]),
            location_id=LocationId(row["location_id"]),
            instrument_id=InstrumentId(row["instrument_id"]),
            balance_kind=_balance_kind_from_row(row),
            target_at=parse_temporal_value(row["target_at"], precision=precision),
            target_precision=precision,
        ),
        quantity=quantity,
        snapshot_basis=row.get("snapshot_basis", ""),
        notes=row.get("notes", ""),
    )


def balance_reference_from_row(row: dict[str, str]) -> BalanceReference:
    target_precision = parse_temporal_precision(row["target_precision"])
    if target_precision is None:
        raise ValueError("missing required enum field: target_precision")
    observed_precision = parse_temporal_precision(row["observed_precision"])
    if observed_precision is None:
        raise ValueError("missing required enum field: observed_precision")
    try:
        reference_kind = BalanceReferenceKind(row["reference_kind"].strip())
    except ValueError as exc:
        raise ValueError("missing required enum field: reference_kind") from exc
    quantity = parse_decimal(row["quantity"])
    if quantity is None:
        raise ValueError("missing required decimal field: quantity")
    return BalanceReference(
        target=BalanceTarget(
            source=SourceId(row["source"]),
            location_id=LocationId(row["location_id"]),
            instrument_id=InstrumentId(row["instrument_id"]),
            balance_kind=_balance_kind_from_row(row),
            target_at=parse_temporal_value(
                row["target_at"],
                precision=target_precision,
            ),
            target_precision=target_precision,
        ),
        quantity=quantity,
        reference_kind=reference_kind,
        observed_at=parse_temporal_value(
            row["observed_at"],
            precision=observed_precision,
        ),
        observed_precision=observed_precision,
        support_ref=row.get("support_ref", ""),
        provider_family=row.get("provider_family", ""),
        provider_locator=row.get("provider_locator", ""),
        provider_block_ref=row.get("provider_block_ref", ""),
        reviewed_by=row.get("reviewed_by", ""),
        reviewed_at=(
            parse_timestamp(row["reviewed_at"])
            if row.get("reviewed_at", "").strip()
            else None
        ),
        notes=row.get("notes", ""),
    )


def _balance_kind_from_row(row: dict[str, str]) -> str:
    return normalize_balance_kind(row.get("balance_kind", ""))
