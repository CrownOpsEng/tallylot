"""Filesystem balance row decoding helpers."""

from __future__ import annotations

from tallylot.domain.checkpoints import BalanceSnapshot, normalize_balance_kind
from tallylot.domain.instruments import InstrumentId
from tallylot.domain.reconciliation import BalanceConfirmation, BalanceEvidence
from tallylot.domain.temporal import parse_temporal_precision
from tallylot.domain.types import LocationId, SourceId
from tallylot.domain.value_objects import (
    parse_decimal,
    parse_temporal_value,
    parse_timestamp,
)


def balance_snapshot_from_row(row: dict[str, str]) -> BalanceSnapshot:
    precision = parse_temporal_precision(row["as_of_precision"])
    if precision is None:
        raise ValueError("missing required enum field: as_of_precision")
    quantity = parse_decimal(row["quantity"])
    if quantity is None:
        raise ValueError("missing required decimal field: quantity")
    return BalanceSnapshot(
        source=SourceId(row["source"]),
        location_id=LocationId(row["location_id"]),
        instrument_id=InstrumentId(row["instrument_id"]),
        quantity=quantity,
        as_of_at=parse_temporal_value(row["as_of_at"], precision=precision),
        as_of_precision=precision,
        balance_kind=_balance_kind_from_row(row),
        notes=row.get("notes", ""),
    )


def balance_evidence_from_row(row: dict[str, str]) -> BalanceEvidence:
    precision = parse_temporal_precision(row["as_of_precision"])
    if precision is None:
        raise ValueError("missing required enum field: as_of_precision")
    quantity = parse_decimal(row["quantity"])
    if quantity is None:
        raise ValueError("missing required decimal field: quantity")
    return BalanceEvidence(
        source=SourceId(row["source"]),
        location_id=LocationId(row["location_id"]),
        instrument_id=InstrumentId(row["instrument_id"]),
        quantity=quantity,
        as_of_at=parse_temporal_value(row["as_of_at"], precision=precision),
        as_of_precision=precision,
        balance_kind=_balance_kind_from_row(row),
        evidence_ref=row.get("evidence_ref", ""),
        notes=row.get("notes", ""),
    )


def balance_confirmation_from_row(row: dict[str, str]) -> BalanceConfirmation:
    precision = parse_temporal_precision(row["as_of_precision"])
    if precision is None:
        raise ValueError("missing required enum field: as_of_precision")
    quantity = parse_decimal(row["quantity"])
    if quantity is None:
        raise ValueError("missing required decimal field: quantity")
    return BalanceConfirmation(
        source=SourceId(row["source"]),
        location_id=LocationId(row["location_id"]),
        instrument_id=InstrumentId(row["instrument_id"]),
        quantity=quantity,
        as_of_at=parse_temporal_value(row["as_of_at"], precision=precision),
        as_of_precision=precision,
        balance_kind=_balance_kind_from_row(row),
        confirmation_kind=row.get("confirmation_kind", ""),
        support_ref=row.get("support_ref", ""),
        asserted_meaning=row.get("asserted_meaning", ""),
        reviewed_by=row.get("reviewed_by", ""),
        reviewed_at=parse_timestamp(row.get("reviewed_at", "")),
        reason=row.get("reason", ""),
        notes=row.get("notes", ""),
    )


def _balance_kind_from_row(row: dict[str, str]) -> str:
    return normalize_balance_kind(row.get("balance_kind", ""))
