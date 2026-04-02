"""Binance spot trade normalization."""

from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.adapters.sources.mapped_event_support import MappedEventSpec, mapped_event
from crypto_reconciliation.domain.models import CanonicalEvent, SourceProfile

from .csv_rows import read_rows
from .field_parsing import amount_with_asset, split_pair
from .timestamps import parse_export_timestamp


def normalize_spot_rows(profile: SourceProfile, path: Path) -> list[CanonicalEvent]:
    events: list[CanonicalEvent] = []
    for index, row in enumerate(read_rows(path), start=2):
        side = (row.get("Side") or "").strip().upper()
        pair = (row.get("Pair") or "").strip().upper()
        base_asset, quote_asset = split_pair(pair)
        executed_amount, executed_asset = amount_with_asset(row.get("Executed", ""))
        quote_amount, _ = amount_with_asset(row.get("Amount", ""))
        fee_amount, fee_asset = amount_with_asset(row.get("Fee", ""))
        timestamp = parse_export_timestamp((row.get("Time") or "").strip(), path.name)
        if side == "SELL":
            events.append(
                mapped_event(
                    MappedEventSpec(
                        event_id=f"binance:{path.name}:row:{index}",
                        source=str(profile.source),
                        adapter_id="binance",
                        account="Spot",
                        wallet="Spot",
                        timestamp=timestamp,
                        event_kind="Trade",
                        description=f"Binance spot sell {pair}",
                        raw_file=path.name,
                        raw_row_ref=f"row:{index}",
                        asset_in=quote_asset,
                        amount_in=quote_amount,
                        asset_out=base_asset or executed_asset,
                        amount_out=executed_amount,
                        fee_asset=fee_asset,
                        fee_amount=fee_amount,
                    )
                )
            )
        elif side == "BUY":
            events.append(
                mapped_event(
                    MappedEventSpec(
                        event_id=f"binance:{path.name}:row:{index}",
                        source=str(profile.source),
                        adapter_id="binance",
                        account="Spot",
                        wallet="Spot",
                        timestamp=timestamp,
                        event_kind="Trade",
                        description=f"Binance spot buy {pair}",
                        raw_file=path.name,
                        raw_row_ref=f"row:{index}",
                        asset_in=base_asset or executed_asset,
                        amount_in=executed_amount,
                        asset_out=quote_asset,
                        amount_out=quote_amount,
                        fee_asset=fee_asset,
                        fee_amount=fee_amount,
                    )
                )
            )
    return events
