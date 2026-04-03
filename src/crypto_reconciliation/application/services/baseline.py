"""Baseline validation service."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from crypto_reconciliation.application.dtos import BaselineValidateRequest, BaselineValidateResponse
from crypto_reconciliation.application.services.export_files import find_required_csv_export
from crypto_reconciliation.domain.value_objects import parse_timestamp
from crypto_reconciliation.ports.artifacts import ArtifactStorePort


class BaselineValidationService:
    def __init__(self, artifacts: ArtifactStorePort) -> None:
        self._artifacts = artifacts

    def execute(self, request: BaselineValidateRequest) -> BaselineValidateResponse:
        trade_table = find_required_csv_export(request.export_dir, "Trade Table")
        current_balance = find_required_csv_export(request.export_dir, "Current Balance")
        exchange_balance = find_required_csv_export(request.export_dir, "Balance by Exchange")
        validate_transactions = find_required_csv_export(request.export_dir, "Validate Transactions")
        missing_transactions = find_required_csv_export(request.export_dir, "Missing Transactions")
        duplicate_transactions = find_required_csv_export(request.export_dir, "Duplicate Transactions")

        trade_rows = self._artifacts.read_rows(trade_table)
        current_rows = self._artifacts.read_rows(current_balance)
        exchange_rows = self._artifacts.read_rows(exchange_balance)
        validate_rows = self._artifacts.read_rows(validate_transactions)
        missing_rows = self._artifacts.read_rows(missing_transactions)
        duplicate_rows = self._artifacts.read_rows(duplicate_transactions)

        latest_timestamp = max(row["Date"] for row in trade_rows if row.get("Date"))
        request.output_dir.mkdir(parents=True, exist_ok=True)

        asset_snapshot = _asset_snapshot(current_rows, exchange_rows)
        exchange_reconciliation = _exchange_reconciliation(current_rows, exchange_rows)
        negative_balances = _negative_balances(current_rows)
        source_activity = _source_activity(trade_rows, exchange_rows)
        cad_flow = _cad_flow_by_type(trade_rows)
        cad_balance_by_exchange = _cad_balances(exchange_rows)

        self._artifacts.write_rows(
            request.output_dir / "baseline_asset_snapshot.csv",
            ("ticker", "current_balance_amount", "exchange_balance_amount", "delta"),
            asset_snapshot,
        )
        self._artifacts.write_rows(
            request.output_dir / "baseline_exchange_reconciliation.csv",
            ("ticker", "current_balance_amount", "exchange_balance_amount", "delta", "status"),
            exchange_reconciliation,
        )
        self._artifacts.write_rows(
            request.output_dir / "baseline_negative_balances.csv",
            ("ticker", "name", "type", "amount", "value_in_cad"),
            negative_balances,
        )
        self._artifacts.write_rows(
            request.output_dir / "baseline_source_activity.csv",
            ("source", "first_timestamp", "last_timestamp", "transaction_count", "has_balance_rows"),
            source_activity,
        )
        self._artifacts.write_rows(
            request.output_dir / "baseline_cad_flow_by_type.csv",
            ("type", "cad_bought", "cad_sold", "cad_fees", "net_cad"),
            cad_flow,
        )
        self._artifacts.write_rows(
            request.output_dir / "baseline_cad_balance_by_exchange.csv",
            ("exchange", "amount", "current_value_cad"),
            cad_balance_by_exchange,
        )
        self._artifacts.write_json(
            request.output_dir / "baseline_summary.json",
            {
                "latest_transaction_timestamp": latest_timestamp,
                "trade_count": len(trade_rows),
                "current_balance_rows": len(current_rows),
                "balance_by_exchange_rows": len(exchange_rows),
                "validate_transactions_rows": len(validate_rows),
                "missing_transactions_rows": len(missing_rows),
                "duplicate_transactions_rows": len(duplicate_rows),
            },
        )
        return BaselineValidateResponse(
            output_dir=request.output_dir,
            latest_timestamp=latest_timestamp,
            asset_count=len(asset_snapshot),
        )


def _asset_snapshot(
    current_rows: list[dict[str, str]],
    exchange_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    exchange_totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for row in exchange_rows:
        exchange_totals[row["Currency"]] += Decimal(row["Amount"])
    return [
        {
            "ticker": row["Ticker"],
            "current_balance_amount": format(Decimal(row["Amount"]), "f"),
            "exchange_balance_amount": format(exchange_totals.get(row["Ticker"], Decimal("0")), "f"),
            "delta": format(Decimal(row["Amount"]) - exchange_totals.get(row["Ticker"], Decimal("0")), "f"),
        }
        for row in current_rows
    ]


def _exchange_reconciliation(
    current_rows: list[dict[str, str]],
    exchange_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    current_by_ticker = {row["Ticker"]: Decimal(row["Amount"]) for row in current_rows}
    exchange_totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for row in exchange_rows:
        exchange_totals[row["Currency"]] += Decimal(row["Amount"])
    all_tickers = sorted(set(current_by_ticker) | set(exchange_totals))
    return [
        {
            "ticker": ticker,
            "current_balance_amount": format(current_by_ticker.get(ticker, Decimal("0")), "f"),
            "exchange_balance_amount": format(exchange_totals.get(ticker, Decimal("0")), "f"),
            "delta": format(
                current_by_ticker.get(ticker, Decimal("0")) - exchange_totals.get(ticker, Decimal("0")),
                "f",
            ),
            "status": (
                "matched"
                if current_by_ticker.get(ticker, Decimal("0")) == exchange_totals.get(ticker, Decimal("0"))
                else "drift"
            ),
        }
        for ticker in all_tickers
    ]


def _negative_balances(current_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        {
            "ticker": row["Ticker"],
            "name": row["Name"],
            "type": row["Type"],
            "amount": format(Decimal(row["Amount"]), "f"),
            "value_in_cad": row["Value in CAD"],
        }
        for row in current_rows
        if Decimal(row["Amount"]) < Decimal("0")
    ]


def _source_activity(
    trade_rows: list[dict[str, str]],
    exchange_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    activity: dict[str, list[str]] = defaultdict(list)
    for row in trade_rows:
        activity[row["Exchange"]].append(row["Date"])
    balance_sources = {row["Exchange"] for row in exchange_rows}
    return [
        {
            "source": source,
            "first_timestamp": min(values, key=parse_timestamp) if values else "",
            "last_timestamp": max(values, key=parse_timestamp) if values else "",
            "transaction_count": str(len(values)),
            "has_balance_rows": "yes" if source in balance_sources else "no",
        }
        for source in sorted(set(activity) | balance_sources)
        for values in (activity.get(source, []),)
    ]


def _cad_flow_by_type(trade_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    totals: dict[str, dict[str, Decimal]] = defaultdict(
        lambda: {
            "cad_bought": Decimal("0"),
            "cad_sold": Decimal("0"),
            "cad_fees": Decimal("0"),
        }
    )
    for row in trade_rows:
        type_totals = totals[row["Type"]]
        if row.get("Cur.") == "CAD" and row.get("Buy"):
            type_totals["cad_bought"] += Decimal(row["Buy"])
        if row.get("Cur..1") == "CAD" and row.get("Sell"):
            type_totals["cad_sold"] += Decimal(row["Sell"])
        if row.get("Cur..2") == "CAD" and row.get("Fee"):
            type_totals["cad_fees"] += Decimal(row["Fee"])
    return [
        {
            "type": event_type,
            "cad_bought": format(values["cad_bought"], "f"),
            "cad_sold": format(values["cad_sold"], "f"),
            "cad_fees": format(values["cad_fees"], "f"),
            "net_cad": format(values["cad_bought"] - values["cad_sold"] - values["cad_fees"], "f"),
        }
        for event_type, values in sorted(totals.items())
    ]


def _cad_balances(exchange_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        {
            "exchange": row["Exchange"],
            "amount": format(Decimal(row["Amount"]), "f"),
            "current_value_cad": row["Current value in CAD"],
        }
        for row in exchange_rows
        if row["Currency"] == "CAD"
    ]
