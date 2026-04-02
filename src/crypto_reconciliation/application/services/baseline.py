"""Baseline validation service."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from crypto_reconciliation.application.dtos import BaselineValidateRequest, BaselineValidateResponse
from crypto_reconciliation.infrastructure.serialization.csv_io import read_rows, write_rows
from crypto_reconciliation.infrastructure.serialization.json_io import write_json


class BaselineValidationService:
    def execute(self, request: BaselineValidateRequest) -> BaselineValidateResponse:
        trade_table = _find_export(request.export_dir, "Trade Table")
        current_balance = _find_export(request.export_dir, "Current Balance")
        exchange_balance = _find_export(request.export_dir, "Balance by Exchange")

        trade_rows = read_rows(trade_table)
        current_rows = read_rows(current_balance)
        exchange_rows = read_rows(exchange_balance)

        latest_timestamp = max(row["Date"] for row in trade_rows if row.get("Date"))
        exchange_totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        for row in exchange_rows:
            exchange_totals[row["Currency"]] += Decimal(row["Amount"])

        asset_snapshot: list[dict[str, str]] = []
        for row in current_rows:
            ticker = row["Ticker"]
            current_amount = Decimal(row["Amount"])
            exchange_amount = exchange_totals.get(ticker, Decimal("0"))
            asset_snapshot.append(
                {
                    "ticker": ticker,
                    "current_balance_amount": format(current_amount, "f"),
                    "exchange_balance_amount": format(exchange_amount, "f"),
                    "delta": format(current_amount - exchange_amount, "f"),
                }
            )

        request.output_dir.mkdir(parents=True, exist_ok=True)
        write_rows(
            request.output_dir / "baseline_asset_snapshot.csv",
            ("ticker", "current_balance_amount", "exchange_balance_amount", "delta"),
            asset_snapshot,
        )
        write_json(
            request.output_dir / "baseline_summary.json",
            {
                "latest_transaction_timestamp": latest_timestamp,
                "trade_count": len(trade_rows),
                "current_balance_rows": len(current_rows),
                "balance_by_exchange_rows": len(exchange_rows),
            },
        )
        return BaselineValidateResponse(
            output_dir=request.output_dir,
            latest_timestamp=latest_timestamp,
            asset_count=len(asset_snapshot),
        )


def _find_export(export_dir: Path, stem: str) -> Path:
    matches = [path for path in export_dir.glob("*.csv") if stem.lower() in path.name.lower()]
    if len(matches) != 1:
        raise FileNotFoundError(f"expected exactly one export containing {stem!r} in {export_dir}")
    return matches[0]
