"""ReconciliationState compatibility projections."""

from __future__ import annotations

from decimal import Decimal
from typing import cast

from tallylot.domain.assertion import QuantityValue
from tallylot.domain.balances import BalanceSnapshot, BalanceTarget
from tallylot.domain.instruments import InstrumentId
from tallylot.domain.reconciliation import (
    ReconciliationState,
)
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.types import LocationId, SourceId


def project_balance_snapshots_from_reconciliation_state(
    reconciliation_state: ReconciliationState,
) -> tuple[BalanceSnapshot, ...]:
    snapshots: list[BalanceSnapshot] = []
    for target in reconciliation_state.balance_target_records:
        expected_value = target.expected_value
        if not isinstance(expected_value, QuantityValue):
            raise ValueError("balance snapshot compatibility requires QuantityValue")
        subject_key = target.subject_ref[1]
        location_ref = _subject_ref_text(subject_key, 1)
        instrument_ref = _subject_ref_text(subject_key, 2)
        snapshots.append(
            BalanceSnapshot(
                target=BalanceTarget(
                    source=SourceId("coinbase"),
                    location_id=LocationId(location_ref),
                    instrument_id=InstrumentId(instrument_ref),
                    balance_kind="available",
                    target_at=target.as_of,
                    target_precision=TemporalPrecision.TIMESTAMP,
                ),
                quantity=Decimal(expected_value.quantity),
                snapshot_basis="fact_cutoff",
            )
        )
    return tuple(
        sorted(
            snapshots,
            key=lambda item: (
                str(item.target.source),
                str(item.target.location_id),
                str(item.target.instrument_id),
                item.target.balance_kind,
                item.target.target_at,
            ),
        )
    )


def _subject_ref_text(subject_key: tuple[object, ...], index: int) -> str:
    value = subject_key[index]
    if not isinstance(value, tuple):
        raise ValueError(
            "balance snapshot compatibility requires position subject refs"
        )
    tuple_value = cast(tuple[object, ...], value)
    if len(tuple_value) != 1 or not isinstance(tuple_value[0], str):
        raise ValueError(
            "balance snapshot compatibility requires position subject refs"
        )
    return tuple_value[0]
