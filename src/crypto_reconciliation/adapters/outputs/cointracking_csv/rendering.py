"""CoinTracking CSV rendering."""

from __future__ import annotations

import csv
from pathlib import Path

from crypto_reconciliation.domain.models import CanonicalEvent
from crypto_reconciliation.domain.value_objects import format_decimal, format_timestamp
from crypto_reconciliation.ports.adapters import RenderedArtifact

from .schema import COINTRACKING_HEADER


def render(events: tuple[CanonicalEvent, ...], output_path: Path) -> RenderedArtifact:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(COINTRACKING_HEADER))
        writer.writeheader()
        for event in events:
            writer.writerow(
                {
                    "Type": event.event_kind,
                    "Buy": format_decimal(event.amount_in),
                    "Cur.": str(event.asset_in or ""),
                    "Sell": format_decimal(event.amount_out),
                    "Cur..1": str(event.asset_out or ""),
                    "Fee": format_decimal(event.fee_amount),
                    "Cur..2": str(event.fee_asset or ""),
                    "Exchange": event.account,
                    "Group": "",
                    "Comment": event.description,
                    "Date": format_timestamp(event.timestamp),
                    "Tx-ID": event.tx_hash or str(event.event_id),
                }
            )
    return RenderedArtifact(
        path=output_path,
        row_count=len(events),
        metadata={"adapter_id": "cointracking_csv"},
    )
