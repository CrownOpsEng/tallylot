"""Boundary parsers for persisted records."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from crypto_reconciliation.domain.models import CanonicalEvent
from crypto_reconciliation.domain.types import AdapterId, AssetSymbol, EventId, SourceId
from crypto_reconciliation.domain.value_objects import parse_decimal
from crypto_reconciliation.infrastructure.serialization.csv_io import read_rows


def load_canonical_events(path: Path) -> tuple[CanonicalEvent, ...]:
    rows = read_rows(path)
    events: list[CanonicalEvent] = []
    for row in rows:
        events.append(
            CanonicalEvent(
                event_id=EventId(row["event_id"]),
                source=SourceId(row["source"]),
                adapter_id=AdapterId(row["adapter_id"]),
                account=row["account"],
                wallet=row["wallet"],
                timestamp=_parse_utc_timestamp(row["timestamp"]),
                event_kind=row["event_kind"],
                description=row["description"],
                asset_in=AssetSymbol(row["asset_in"]) if row["asset_in"] else None,
                amount_in=parse_decimal(row["amount_in"]),
                asset_out=AssetSymbol(row["asset_out"]) if row["asset_out"] else None,
                amount_out=parse_decimal(row["amount_out"]),
                fee_asset=AssetSymbol(row["fee_asset"]) if row["fee_asset"] else None,
                fee_amount=parse_decimal(row["fee_amount"]),
                tx_hash=row["tx_hash"] or None,
                raw_file=row["raw_file"],
                raw_row_ref=row["raw_row_ref"],
                confidence=row["confidence"],
                status=row["status"],
                render_type=row["render_type"] or None,
                render_exchange=row["render_exchange"] or None,
                render_group=row["render_group"] or None,
                render_comment=row["render_comment"] or None,
            )
        )
    return tuple(events)


def _parse_utc_timestamp(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
