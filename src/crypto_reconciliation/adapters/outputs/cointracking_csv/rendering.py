"""CoinTracking CSV rendering."""

from __future__ import annotations

import csv
from pathlib import Path

from crypto_reconciliation.domain.models import NormalizedTransaction
from crypto_reconciliation.domain.value_objects import format_decimal, format_timestamp
from crypto_reconciliation.ports.adapters import RenderedArtifact

from .mapping import cointracking_type_for
from .schema import COINTRACKING_HEADER


def render(transactions: tuple[NormalizedTransaction, ...], output_path: Path) -> RenderedArtifact:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(COINTRACKING_HEADER))
        writer.writeheader()
        for transaction in transactions:
            writer.writerow(
                {
                    "Type": cointracking_type_for(transaction.category),
                    "Buy": format_decimal(transaction.amount_in),
                    "Cur.": str(transaction.asset_in or ""),
                    "Sell": format_decimal(transaction.amount_out),
                    "Cur..1": str(transaction.asset_out or ""),
                    "Fee": format_decimal(transaction.fee_amount),
                    "Cur..2": str(transaction.fee_asset or ""),
                    "Exchange": transaction.account,
                    "Group": "",
                    "Comment": transaction.description,
                    "Date": format_timestamp(transaction.timestamp),
                    "Tx-ID": transaction.tx_hash or str(transaction.transaction_id),
                }
            )
    return RenderedArtifact(
        path=output_path,
        row_count=len(transactions),
        metadata={"adapter_id": "cointracking_csv"},
    )
