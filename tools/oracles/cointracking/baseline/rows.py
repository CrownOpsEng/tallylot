"""Typed CoinTracking baseline export row models."""

from __future__ import annotations
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from tallylot.ports.artifacts import ArtifactStorePort

from ..screening_columns import cell, load_cointracking_rows
from .row_models import (
    BalanceByExchangeRowModel,
    BaselineRowModel,
    CurrentBalanceRowModel,
    DuplicateTransactionsRowModel,
    MissingTransactionsRowModel,
    TradeTableRowModel,
    ValidateTransactionsRowModel,
)


_BASELINE_ROW_MODELS: dict[str, type[BaselineRowModel]] = {
    "Trade Table": TradeTableRowModel,
    "Current Balance": CurrentBalanceRowModel,
    "Balance by Exchange": BalanceByExchangeRowModel,
    "Validate Transactions": ValidateTransactionsRowModel,
    "Missing Transactions": MissingTransactionsRowModel,
    "Duplicate Transactions": DuplicateTransactionsRowModel,
}


@dataclass(frozen=True)
class BaselineExportRows:
    trade_rows: tuple[Mapping[str, str], ...]
    current_rows: tuple[Mapping[str, str], ...]
    exchange_rows: tuple[Mapping[str, str], ...]
    validate_rows: tuple[Mapping[str, str], ...]
    missing_rows: tuple[Mapping[str, str], ...]
    duplicate_rows: tuple[Mapping[str, str], ...]


def read_baseline_export_rows(
    exports: dict[str, Path],
    artifacts: ArtifactStorePort,
) -> BaselineExportRows:
    return BaselineExportRows(
        trade_rows=parse_baseline_export_rows(
            "Trade Table", _read_trade_table_export_rows(exports["Trade Table"])
        ),
        current_rows=parse_baseline_export_rows(
            "Current Balance",
            _read_current_balance_rows(exports["Current Balance"], artifacts),
        ),
        exchange_rows=parse_baseline_export_rows(
            "Balance by Exchange",
            artifacts.read_rows(exports["Balance by Exchange"]),
        ),
        validate_rows=parse_baseline_export_rows(
            "Validate Transactions",
            _read_validate_transaction_rows(
                exports["Validate Transactions"], artifacts
            ),
        ),
        missing_rows=parse_baseline_export_rows(
            "Missing Transactions",
            artifacts.read_rows(exports["Missing Transactions"]),
        ),
        duplicate_rows=parse_baseline_export_rows(
            "Duplicate Transactions",
            artifacts.read_rows(exports["Duplicate Transactions"]),
        ),
    )


def parse_baseline_export_rows(
    stem: str, rows: Iterable[dict[str, str]]
) -> tuple[Mapping[str, str], ...]:
    row_model = _BASELINE_ROW_MODELS.get(stem)
    if row_model is None:
        raise ValueError(f"Unsupported CoinTracking baseline export family: {stem}")
    return tuple(
        MappingProxyType(
            row_model.model_validate(_normalize_blank_header(row)).to_row()
        )
        for row in rows
    )


def _normalize_blank_header(row: dict[str, str]) -> dict[str, str]:
    if "" not in row:
        return row
    unnamed_value = (row.get("") or "").strip()
    if unnamed_value:
        return row
    return {key: value for key, value in row.items() if key}


def _read_trade_table_export_rows(path: Path) -> tuple[dict[str, str], ...]:
    header, rows, _ = load_cointracking_rows(path)
    columns = _build_trade_table_column_map(header)
    used_indexes = {index for index in columns.values() if index is not None}
    normalized_rows: list[dict[str, str]] = []
    for row in rows:
        _validate_trade_table_extra_columns(path, header, row, used_indexes)
        normalized_rows.append(
            {
                "Type": cell(row, columns["type"]),
                "Buy": cell(row, columns["buy"]),
                "Cur.": cell(row, columns["buy_currency"]),
                "Sell": cell(row, columns["sell"]),
                "Cur..1": cell(row, columns["sell_currency"]),
                "Fee": cell(row, columns["fee"]),
                "Cur..2": cell(row, columns["fee_currency"]),
                "Exchange": cell(row, columns["exchange"]),
                "Group": cell(row, columns["group"]),
                "Comment": cell(row, columns["comment"]),
                "Date": cell(row, columns["date"]),
                "Tx-ID": cell(row, columns["tx_id"]),
            }
        )
    return tuple(normalized_rows)


def _read_current_balance_rows(
    path: Path,
    artifacts: ArtifactStorePort,
) -> tuple[dict[str, str], ...]:
    return _trim_known_extra_columns(
        path,
        artifacts.read_rows(path),
        required_headers={"Ticker", "Name", "Type", "Amount", "Value in CAD"},
        optional_headers={
            "Value in BTC",
            "% of total",
            "Price in BTC",
            "Price in CAD",
            "Trend 1h in %",
            "Trend 24h in %",
            "Trend 7d in %",
            "Trend 30d in %",
        },
    )


def _read_validate_transaction_rows(
    path: Path,
    artifacts: ArtifactStorePort,
) -> tuple[dict[str, str], ...]:
    rows = artifacts.read_rows(path)
    if not rows:
        return ()
    if all("Issue" in row for row in rows):
        return tuple({"Issue": row["Issue"]} for row in rows)
    normalized_rows: list[dict[str, str]] = []
    for row in rows:
        issue_parts = [
            value
            for value in (
                (row.get("Urgency") or "").strip(),
                (row.get("Type") or "").strip(),
                (row.get("Exchange") or "").strip(),
                (row.get("Trade Date") or row.get("Date") or "").strip(),
            )
            if value
        ]
        normalized_rows.append({"Issue": " | ".join(issue_parts)})
    return tuple(normalized_rows)


def _build_trade_table_column_map(header: list[str]) -> dict[str, int | None]:
    type_index = _find_header_index(header, "Type")
    buy_index = _find_header_index(header, "Buy")
    sell_index = _find_header_index(header, "Sell")
    fee_index = _find_header_index(header, "Fee")
    buy_currency_index = _find_next_header_index(header, "Cur.", buy_index)
    sell_currency_index = _find_header_index(header, "Cur..1")
    if sell_currency_index is None:
        sell_currency_index = _find_next_header_index(header, "Cur.", sell_index)
    fee_currency_index = _find_header_index(header, "Cur..2")
    if fee_currency_index is None:
        fee_currency_index = _find_next_header_index(header, "Cur.", fee_index)
    exchange_index = _find_header_index(header, "Exchange")
    group_index = _find_header_index(header, "Group")
    comment_index = _find_header_index(header, "Comment")
    date_index = _find_header_index(header, "Date")
    tx_id_index = _find_header_index(header, "Tx-ID")
    if tx_id_index is None:
        tx_id_index = _find_header_index(header, "Tx ID")

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


def _validate_trade_table_extra_columns(
    path: Path,
    header: list[str],
    row: list[str],
    used_indexes: set[int],
) -> None:
    for index, column_name in enumerate(header):
        if index in used_indexes or index >= len(row):
            continue
        value = row[index].strip()
        if not value:
            continue
        if column_name == "LPN":
            raise ValueError(
                f"Unsupported non-blank CoinTracking Trade Table LPN value in {path}"
            )
        raise ValueError(
            f"Unsupported non-blank CoinTracking Trade Table column {column_name!r} in {path}"
        )


def _trim_known_extra_columns(
    path: Path,
    rows: Iterable[dict[str, str]],
    *,
    required_headers: set[str],
    optional_headers: set[str],
) -> tuple[dict[str, str], ...]:
    normalized_rows: list[dict[str, str]] = []
    known_headers = required_headers | optional_headers
    for row in rows:
        normalized_row = {
            key: value for key, value in row.items() if key in required_headers
        }
        missing_headers = sorted(
            header for header in required_headers if header not in normalized_row
        )
        if missing_headers:
            missing_text = ", ".join(missing_headers)
            raise ValueError(f"Missing required headers in {path}: {missing_text}")
        for key, value in row.items():
            if key in known_headers or not (value or "").strip():
                continue
            raise ValueError(f"Unsupported non-blank column {key!r} in {path}")
        normalized_rows.append(normalized_row)
    return tuple(normalized_rows)


def _find_header_index(header: list[str], name: str) -> int | None:
    try:
        return header.index(name)
    except ValueError:
        return None


def _find_next_header_index(
    header: list[str], name: str, start: int | None
) -> int | None:
    if start is None:
        return None
    for index in range(start + 1, len(header)):
        if header[index] == name:
            return index
    return None
