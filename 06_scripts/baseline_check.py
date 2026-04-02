#!/usr/bin/env python3

"""Generate baseline validation artifacts from a CoinTracking full export."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Sequence

from script_common import decimal_text, find_required_csv_exports, read_csv_rows, require_directory, write_csv_rows, write_json


REQUIRED_FILES = {
    "trade_table": "Trade Table",
    "current_balance": "Current Balance",
    "balance_by_exchange": "Balance by Exchange",
    "validate_transactions": "Validate Transactions",
    "missing_transactions": "Missing Transactions",
    "duplicate_transactions": "Duplicate Transactions",
}

def find_required_files(export_dir: Path) -> dict[str, Path]:
    return find_required_csv_exports(export_dir, REQUIRED_FILES, "Export directory")


def parse_trade_table_row(row: Sequence[str]) -> tuple[str, Decimal, str, Decimal, str, Decimal, str]:
    if len(row) < 11:
        raise ValueError(f"Trade row is too short: {row!r}")
    return (
        row[0],
        Decimal(row[1] or "0"),
        row[2],
        Decimal(row[3] or "0"),
        row[4],
        Decimal(row[5] or "0"),
        row[6],
    )


def latest_trade_timestamp(trade_rows: list[dict[str, str]]) -> datetime:
    dated_rows = [row["Date"] for row in trade_rows if row.get("Date")]
    if not dated_rows:
        raise ValueError("Trade Table export did not contain any dated rows")
    return max(datetime.strptime(value, "%Y-%m-%d %H:%M:%S") for value in dated_rows)


def build_source_activity(
    trade_rows: list[dict[str, str]],
    balance_by_exchange_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    trade_summary: dict[str, dict[str, object]] = defaultdict(
        lambda: {"count": 0, "first": None, "last": None}
    )
    balance_summary: dict[str, dict[str, object]] = defaultdict(
        lambda: {"count": 0, "assets": set()}
    )

    for row in trade_rows:
        source = row["Exchange"]
        if not source:
            continue
        trade_dt = datetime.strptime(row["Date"], "%Y-%m-%d %H:%M:%S")
        source_summary = trade_summary[source]
        source_summary["count"] = int(source_summary["count"]) + 1
        first_trade = source_summary["first"]
        last_trade = source_summary["last"]
        source_summary["first"] = trade_dt if first_trade is None else min(first_trade, trade_dt)
        source_summary["last"] = trade_dt if last_trade is None else max(last_trade, trade_dt)

    for row in balance_by_exchange_rows:
        source = row["Exchange"]
        if not source:
            continue
        source_summary = balance_summary[source]
        source_summary["count"] = int(source_summary["count"]) + 1
        source_summary["assets"].add(row["Currency"])

    rows = []
    for source in sorted(set(trade_summary) | set(balance_summary)):
        trade_info = trade_summary.get(source, {})
        balance_info = balance_summary.get(source, {})
        first_trade = trade_info.get("first")
        last_trade = trade_info.get("last")
        rows.append(
            {
                "source": source,
                "first_trade_timestamp": (
                    first_trade.strftime("%Y-%m-%d %H:%M:%S") if isinstance(first_trade, datetime) else ""
                ),
                "last_trade_timestamp": (
                    last_trade.strftime("%Y-%m-%d %H:%M:%S") if isinstance(last_trade, datetime) else ""
                ),
                "trade_table_rows": str(trade_info.get("count", 0)),
                "balance_by_exchange_rows": str(balance_info.get("count", 0)),
                "balance_asset_count": str(len(balance_info.get("assets", set()))),
                "present_in_trade_table": "yes" if source in trade_summary else "no",
                "present_in_balance_by_exchange": "yes" if source in balance_summary else "no",
            }
        )
    return rows


def build_asset_snapshot(current_balance_rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], dict[str, Decimal], list[dict[str, str]]]:
    asset_snapshot_rows = []
    current_by_ticker: dict[str, Decimal] = {}
    negative_balances: list[dict[str, str]] = []
    for row in sorted(current_balance_rows, key=lambda item: item["Ticker"]):
        amount = Decimal(row["Amount"])
        current_by_ticker[row["Ticker"]] = amount
        snapshot_row = {
            "ticker": row["Ticker"],
            "name": row["Name"],
            "type": row["Type"],
            "amount": decimal_text(amount),
            "value_cad": row["Value in CAD"],
        }
        asset_snapshot_rows.append(snapshot_row)
        if amount < 0:
            negative_balances.append(snapshot_row)
    return asset_snapshot_rows, current_by_ticker, negative_balances


def build_exchange_reconciliation(
    current_by_ticker: dict[str, Decimal],
    balance_by_exchange_rows: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[dict[str, str]], Decimal, str]:
    exchange_totals: dict[str, Decimal] = defaultdict(Decimal)
    cad_balance_by_exchange_rows: list[dict[str, str]] = []
    for row in balance_by_exchange_rows:
        exchange_totals[row["Currency"]] += Decimal(row["Amount"])
        if row["Currency"] == "CAD":
            cad_balance_by_exchange_rows.append(
                {
                    "exchange": row["Exchange"],
                    "cad_amount": decimal_text(Decimal(row["Amount"])),
                    "value_cad": row["Current value in CAD"],
                }
            )

    reconciliation_rows = []
    max_abs_difference = Decimal("0")
    max_abs_difference_ticker = ""
    all_tickers = sorted(set(current_by_ticker) | set(exchange_totals))
    for ticker in all_tickers:
        current_amount = current_by_ticker.get(ticker, Decimal("0"))
        exchange_amount = exchange_totals.get(ticker, Decimal("0"))
        difference = exchange_amount - current_amount
        if abs(difference) > abs(max_abs_difference):
            max_abs_difference = difference
            max_abs_difference_ticker = ticker
        reconciliation_rows.append(
            {
                "ticker": ticker,
                "current_balance_amount": decimal_text(current_amount),
                "balance_by_exchange_amount": decimal_text(exchange_amount),
                "difference": decimal_text(difference),
                "status": "match" if difference == 0 else "drift",
            }
        )
    return reconciliation_rows, cad_balance_by_exchange_rows, max_abs_difference, max_abs_difference_ticker


def build_cad_flow_summary(trade_table_path: Path) -> tuple[list[dict[str, str]], Decimal, Decimal, Decimal]:
    cad_flow_by_type: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    cad_sold_total = Decimal("0")
    cad_bought_total = Decimal("0")
    cad_fee_total = Decimal("0")
    with trade_table_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        next(reader, None)
        for row in reader:
            trade_type, buy, buy_cur, sell, sell_cur, fee, fee_cur = parse_trade_table_row(row)

            if buy_cur == "CAD":
                cad_bought_total += buy
                cad_flow_by_type[trade_type]["cad_bought"] += buy
            if sell_cur == "CAD":
                cad_sold_total += sell
                cad_flow_by_type[trade_type]["cad_sold"] += sell
            if fee_cur == "CAD":
                cad_fee_total += fee
                cad_flow_by_type[trade_type]["cad_fee"] += fee

    cad_flow_rows = []
    for trade_type in sorted(cad_flow_by_type):
        cad_bought = cad_flow_by_type[trade_type]["cad_bought"]
        cad_sold = cad_flow_by_type[trade_type]["cad_sold"]
        cad_fee = cad_flow_by_type[trade_type]["cad_fee"]
        cad_flow_rows.append(
            {
                "type": trade_type,
                "cad_bought": decimal_text(cad_bought),
                "cad_sold": decimal_text(cad_sold),
                "cad_fee": decimal_text(cad_fee),
                "net_cad_balance_impact": decimal_text(cad_bought - cad_sold),
                "net_cad_after_fees": decimal_text(cad_bought - cad_sold - cad_fee),
            }
        )
    return cad_flow_rows, cad_bought_total, cad_sold_total, cad_fee_total


def build_baseline_artifacts(export_dir: Path) -> dict[str, object]:
    export_dir = require_directory(export_dir.resolve(), "Export directory")
    files = find_required_files(export_dir)
    trade_rows = read_csv_rows(files["trade_table"])
    current_balance_rows = read_csv_rows(files["current_balance"])
    balance_by_exchange_rows = read_csv_rows(files["balance_by_exchange"])
    validate_rows = read_csv_rows(files["validate_transactions"])
    missing_rows = read_csv_rows(files["missing_transactions"])
    duplicate_rows = read_csv_rows(files["duplicate_transactions"])

    latest_trade = latest_trade_timestamp(trade_rows)
    asset_snapshot_rows, current_by_ticker, negative_balances = build_asset_snapshot(current_balance_rows)
    (
        reconciliation_rows,
        cad_balance_by_exchange_rows,
        max_abs_difference,
        max_abs_difference_ticker,
    ) = build_exchange_reconciliation(current_by_ticker, balance_by_exchange_rows)
    source_activity_rows = build_source_activity(trade_rows, balance_by_exchange_rows)
    cad_flow_rows, cad_bought_total, cad_sold_total, cad_fee_total = build_cad_flow_summary(
        files["trade_table"]
    )

    ending_cad_balance = current_by_ticker.get("CAD", Decimal("0"))

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "export_dir": str(export_dir),
        "trade_table_file": files["trade_table"].name,
        "current_balance_file": files["current_balance"].name,
        "balance_by_exchange_file": files["balance_by_exchange"].name,
        "validate_transactions_file": files["validate_transactions"].name,
        "missing_transactions_file": files["missing_transactions"].name,
        "duplicate_transactions_file": files["duplicate_transactions"].name,
        "latest_transaction_timestamp": latest_trade.strftime("%Y-%m-%d %H:%M:%S"),
        "trade_table_rows": len(trade_rows),
        "current_balance_rows": len(current_balance_rows),
        "balance_by_exchange_rows": len(balance_by_exchange_rows),
        "validate_transactions_rows": len(validate_rows),
        "missing_transactions_rows": len(missing_rows),
        "duplicate_transactions_rows": len(duplicate_rows),
        "negative_balance_rows": len(negative_balances),
        "negative_balances": negative_balances,
        "asset_reconciliation_assets": len(reconciliation_rows),
        "max_asset_difference": decimal_text(max_abs_difference),
        "max_asset_difference_ticker": max_abs_difference_ticker,
        "trade_table_sources": len({row["Exchange"] for row in trade_rows if row.get("Exchange")}),
        "balance_by_exchange_sources": len(
            {row["Exchange"] for row in balance_by_exchange_rows if row.get("Exchange")}
        ),
        "source_activity_rows": len(source_activity_rows),
        "ending_cad_balance": decimal_text(ending_cad_balance),
        "cad_bought_total": decimal_text(cad_bought_total),
        "cad_sold_total": decimal_text(cad_sold_total),
        "cad_fee_total": decimal_text(cad_fee_total),
        "cad_net_balance_impact": decimal_text(cad_bought_total - cad_sold_total),
        "cad_net_after_fees": decimal_text(cad_bought_total - cad_sold_total - cad_fee_total),
    }
    return {
        "asset_snapshot_rows": asset_snapshot_rows,
        "reconciliation_rows": reconciliation_rows,
        "negative_balances": negative_balances,
        "source_activity_rows": source_activity_rows,
        "cad_flow_rows": cad_flow_rows,
        "cad_balance_by_exchange_rows": cad_balance_by_exchange_rows,
        "summary": summary,
    }


def write_baseline_artifacts(out_dir: Path, artifacts: dict[str, object]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv_rows(
        out_dir / "baseline_asset_snapshot.csv",
        ["ticker", "name", "type", "amount", "value_cad"],
        artifacts["asset_snapshot_rows"],
    )
    write_csv_rows(
        out_dir / "baseline_exchange_reconciliation.csv",
        ["ticker", "current_balance_amount", "balance_by_exchange_amount", "difference", "status"],
        artifacts["reconciliation_rows"],
    )
    write_csv_rows(
        out_dir / "baseline_negative_balances.csv",
        ["ticker", "name", "type", "amount", "value_cad"],
        artifacts["negative_balances"],
    )
    write_csv_rows(
        out_dir / "baseline_source_activity.csv",
        [
            "source",
            "first_trade_timestamp",
            "last_trade_timestamp",
            "trade_table_rows",
            "balance_by_exchange_rows",
            "balance_asset_count",
            "present_in_trade_table",
            "present_in_balance_by_exchange",
        ],
        artifacts["source_activity_rows"],
    )
    write_csv_rows(
        out_dir / "baseline_cad_flow_by_type.csv",
        ["type", "cad_bought", "cad_sold", "cad_fee", "net_cad_balance_impact", "net_cad_after_fees"],
        artifacts["cad_flow_rows"],
    )
    write_csv_rows(
        out_dir / "baseline_cad_balance_by_exchange.csv",
        ["exchange", "cad_amount", "value_cad"],
        artifacts["cad_balance_by_exchange_rows"],
    )
    write_json(out_dir / "baseline_summary.json", artifacts["summary"])


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--export-dir", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    out_dir = args.out_dir.resolve()
    artifacts = build_baseline_artifacts(args.export_dir)
    write_baseline_artifacts(out_dir, artifacts)
    print(json.dumps(artifacts["summary"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
