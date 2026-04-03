"""CoinTracking CSV column and row parsing helpers."""

from __future__ import annotations

import csv
from pathlib import Path

TX_ID_HEADERS = ("Tx-ID", "Tx ID", "Trade ID", "Transaction ID")


def load_cointracking_rows(path: Path) -> tuple[list[str], list[list[str]], dict[str, int | None]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)
        header = next(reader, None)
        if header is None:
            raise ValueError(f"CSV file is empty: {path}")
        rows = [row for row in reader if any(cell.strip() for cell in row)]
    columns = build_cointracking_column_map(header)
    return header, rows, columns


def build_cointracking_column_map(header: list[str]) -> dict[str, int | None]:
    type_index = _find_header_index(header, "Type")
    buy_index = _find_header_index(header, "Buy")
    sell_index = _find_header_index(header, "Sell")
    fee_index = _find_header_index(header, "Fee")
    buy_currency_index = _find_next_header_index(header, "Cur.", buy_index) if buy_index is not None else None
    sell_currency_index = _find_next_header_index(header, "Cur.", sell_index) if sell_index is not None else None
    fee_currency_index = _find_next_header_index(header, "Cur.", fee_index) if fee_index is not None else None
    date_index = _find_header_index(header, "Date")
    if date_index is None:
        date_index = _find_header_index(header, "Trade Date")
    exchange_index = _find_header_index(header, "Exchange")
    group_index = _find_header_index(header, "Group")
    if group_index is None:
        group_index = _find_header_index(header, "Trade Group")
    comment_index = _find_header_index(header, "Comment")

    tx_id_index = None
    for header_name in TX_ID_HEADERS:
        tx_id_index = _find_header_index(header, header_name)
        if tx_id_index is not None:
            break

    if type_index is None or date_index is None:
        raise ValueError("Candidate file must contain at least 'Type' and 'Date' or 'Trade Date' columns")

    return {
        "type": type_index,
        "buy": buy_index,
        "buy_currency": buy_currency_index,
        "sell": sell_index,
        "sell_currency": sell_currency_index,
        "fee": fee_index,
        "fee_currency": fee_currency_index,
        "exchange": exchange_index,
        "group": group_index,
        "comment": comment_index,
        "date": date_index,
        "tx_id": tx_id_index,
    }


def cell(row: list[str], index: int | None) -> str:
    if index is None or index >= len(row):
        return ""
    return row[index].strip()


def overlap_signature(row: list[str], columns: dict[str, int | None]) -> tuple[str, ...]:
    return (
        cell(row, columns["type"]),
        cell(row, columns["buy"]),
        cell(row, columns["buy_currency"]),
        cell(row, columns["sell"]),
        cell(row, columns["sell_currency"]),
        cell(row, columns["fee"]),
        cell(row, columns["fee_currency"]),
        cell(row, columns["exchange"]),
        cell(row, columns["date"]),
    )


def _find_header_index(header: list[str], name: str) -> int | None:
    try:
        return header.index(name)
    except ValueError:
        return None


def _find_next_header_index(header: list[str], name: str, start: int) -> int | None:
    for index in range(start + 1, len(header)):
        if header[index] == name:
            return index
    return None
