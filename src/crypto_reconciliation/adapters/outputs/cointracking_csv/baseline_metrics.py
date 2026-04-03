"""CoinTracking baseline analysis helpers."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from decimal import Decimal

from crypto_reconciliation.domain.value_objects import format_timestamp, parse_timestamp


def decimal_text(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.00000000")), "f")


def parse_trade_table_row(row: list[str]) -> tuple[str, Decimal, str, Decimal, str, Decimal, str]:
    if len(row) < 7:
        raise ValueError("Trade Table row is too short to parse")
    return (
        row[0].strip(),
        _decimal_or_zero(row[1]),
        row[2].strip(),
        _decimal_or_zero(row[3]),
        row[4].strip(),
        _decimal_or_zero(row[5]),
        row[6].strip(),
    )


def latest_trade_timestamp(trade_rows: list[dict[str, str]]) -> datetime:
    dated_rows: list[datetime] = []
    for row in trade_rows:
        date_value = (row.get("Date") or "").strip()
        if not date_value:
            continue
        dated_rows.append(parse_timestamp(date_value))
    if not dated_rows:
        raise ValueError("Trade Table did not contain any dated rows")
    return max(dated_rows)


def build_asset_snapshot(
    current_rows: list[dict[str, str]],
    exchange_rows: list[dict[str, str]],
) -> tuple[list[dict[str, str]], dict[str, Decimal], list[dict[str, str]]]:
    exchange_totals = _exchange_totals_by_asset(exchange_rows)
    current_by_ticker = {row["Ticker"]: _decimal_or_zero(row["Amount"]) for row in current_rows}
    snapshot_rows = [
        {
            "ticker": ticker,
            "current_balance_amount": decimal_text(current_by_ticker[ticker]),
            "balance_by_exchange_amount": decimal_text(exchange_totals.get(ticker, Decimal("0"))),
            "difference": decimal_text(current_by_ticker[ticker] - exchange_totals.get(ticker, Decimal("0"))),
        }
        for ticker in sorted(current_by_ticker)
    ]
    negative_balances = [
        {
            "ticker": row["Ticker"],
            "name": row["Name"],
            "type": row["Type"],
            "amount": decimal_text(_decimal_or_zero(row["Amount"])),
            "value_cad": row["Value in CAD"],
        }
        for row in current_rows
        if _decimal_or_zero(row["Amount"]) < Decimal("0")
    ]
    return snapshot_rows, current_by_ticker, negative_balances


def build_exchange_reconciliation(
    current_by_ticker: dict[str, Decimal],
    exchange_rows: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[dict[str, str]], Decimal, str]:
    exchange_totals = _exchange_totals_by_asset(exchange_rows)
    reconciliation_rows: list[dict[str, str]] = []
    max_difference = Decimal("0")
    max_ticker = ""
    for ticker in sorted(set(current_by_ticker) | set(exchange_totals)):
        current_amount = current_by_ticker.get(ticker, Decimal("0"))
        exchange_amount = exchange_totals.get(ticker, Decimal("0"))
        difference = abs(current_amount - exchange_amount)
        if difference > max_difference:
            max_difference = difference
            max_ticker = ticker
        reconciliation_rows.append(
            {
                "ticker": ticker,
                "current_balance_amount": decimal_text(current_amount),
                "balance_by_exchange_amount": decimal_text(exchange_amount),
                "difference": decimal_text(difference),
                "status": "matched" if difference == Decimal("0") else "drift",
            }
        )
    cad_rows = [
        {
            "exchange": row["Exchange"],
            "amount": decimal_text(_decimal_or_zero(row["Amount"])),
            "current_value_cad": row["Current value in CAD"],
        }
        for row in exchange_rows
        if row["Currency"] == "CAD"
    ]
    return reconciliation_rows, cad_rows, max_difference, max_ticker


def build_source_activity(
    trade_rows: list[dict[str, str]],
    exchange_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    trade_dates_by_source: dict[str, list[datetime]] = defaultdict(list)
    trade_row_counts: dict[str, int] = defaultdict(int)
    balance_row_counts: dict[str, int] = defaultdict(int)
    balance_assets: dict[str, set[str]] = defaultdict(set)
    for row in trade_rows:
        source = row["Exchange"]
        trade_row_counts[source] += 1
        date_value = (row.get("Date") or "").strip()
        if date_value:
            trade_dates_by_source[source].append(parse_timestamp(date_value))
    for row in exchange_rows:
        source = row["Exchange"]
        balance_row_counts[source] += 1
        currency = (row.get("Currency") or "").strip()
        if currency:
            balance_assets[source].add(currency)
    rows: list[dict[str, str]] = []
    for source in sorted(set(trade_row_counts) | set(balance_row_counts)):
        dates = trade_dates_by_source.get(source, [])
        rows.append(
            {
                "source": source,
                "first_trade_timestamp": "" if not dates else format_timestamp(min(dates)),
                "last_trade_timestamp": "" if not dates else format_timestamp(max(dates)),
                "trade_table_rows": str(trade_row_counts.get(source, 0)),
                "balance_by_exchange_rows": str(balance_row_counts.get(source, 0)),
                "balance_asset_count": str(len(balance_assets.get(source, set()))),
                "present_in_trade_table": "yes" if trade_row_counts.get(source, 0) else "no",
                "present_in_balance_by_exchange": "yes" if balance_row_counts.get(source, 0) else "no",
            }
        )
    return rows


def build_cad_flow_summary(
    trade_rows: list[dict[str, str]],
) -> tuple[list[dict[str, str]], Decimal, Decimal, Decimal]:
    totals: dict[str, dict[str, Decimal]] = defaultdict(
        lambda: {
            "cad_bought": Decimal("0"),
            "cad_sold": Decimal("0"),
            "cad_fees": Decimal("0"),
        }
    )
    for row in trade_rows:
        type_totals = totals[row["Type"]]
        if (row.get("Cur.") or "").strip() == "CAD":
            type_totals["cad_bought"] += _decimal_or_zero(row.get("Buy", ""))
        if (row.get("Cur..1") or "").strip() == "CAD":
            type_totals["cad_sold"] += _decimal_or_zero(row.get("Sell", ""))
        if (row.get("Cur..2") or "").strip() == "CAD":
            type_totals["cad_fees"] += _decimal_or_zero(row.get("Fee", ""))
    rows = [
        {
            "type": event_type,
            "cad_bought": decimal_text(values["cad_bought"]),
            "cad_sold": decimal_text(values["cad_sold"]),
            "cad_fees": decimal_text(values["cad_fees"]),
            "net_cad": decimal_text(values["cad_bought"] - values["cad_sold"] - values["cad_fees"]),
        }
        for event_type, values in sorted(totals.items())
        if values["cad_bought"] or values["cad_sold"] or values["cad_fees"]
    ]
    cad_bought_total = sum((values["cad_bought"] for values in totals.values()), start=Decimal("0"))
    cad_sold_total = sum((values["cad_sold"] for values in totals.values()), start=Decimal("0"))
    cad_fee_total = sum((values["cad_fees"] for values in totals.values()), start=Decimal("0"))
    return rows, cad_bought_total, cad_sold_total, cad_fee_total


def _decimal_or_zero(value: str | Decimal) -> Decimal:
    if isinstance(value, Decimal):
        return value
    text = value.strip()
    return Decimal("0") if not text else Decimal(text)


def _exchange_totals_by_asset(exchange_rows: list[dict[str, str]]) -> dict[str, Decimal]:
    totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for row in exchange_rows:
        totals[row["Currency"]] += _decimal_or_zero(row["Amount"])
    return dict(totals)
