"""CoinTracking CSV rendering."""

from __future__ import annotations

import csv
from pathlib import Path

from crypto_reconciliation.domain.models import NormalizedTransaction
from crypto_reconciliation.ports.adapters import RenderedArtifact

from .projection import cointracking_row
from .schema import COINTRACKING_HEADER


def render(transactions: tuple[NormalizedTransaction, ...], output_path: Path) -> RenderedArtifact:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(COINTRACKING_HEADER))
        writer.writeheader()
        for transaction in transactions:
            row = cointracking_row(transaction)
            writer.writerow({field: row[field] for field in COINTRACKING_HEADER})
    return RenderedArtifact(
        path=output_path,
        row_count=len(transactions),
        metadata={"adapter_id": "cointracking_csv"},
    )
