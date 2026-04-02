"""Typed CoinTracking baseline export row models."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from tallylot.ports.artifacts import ArtifactStorePort
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
    trade_rows: list[dict[str, str]]
    current_rows: list[dict[str, str]]
    exchange_rows: list[dict[str, str]]
    validate_rows: list[dict[str, str]]
    missing_rows: list[dict[str, str]]
    duplicate_rows: list[dict[str, str]]


def read_baseline_export_rows(
    exports: dict[str, Path],
    artifacts: ArtifactStorePort,
) -> BaselineExportRows:
    return BaselineExportRows(
        trade_rows=parse_baseline_export_rows(
            "Trade Table", artifacts.read_rows(exports["Trade Table"])
        ),
        current_rows=parse_baseline_export_rows(
            "Current Balance", artifacts.read_rows(exports["Current Balance"])
        ),
        exchange_rows=parse_baseline_export_rows(
            "Balance by Exchange",
            artifacts.read_rows(exports["Balance by Exchange"]),
        ),
        validate_rows=parse_baseline_export_rows(
            "Validate Transactions",
            artifacts.read_rows(exports["Validate Transactions"]),
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
) -> list[dict[str, str]]:
    row_model = _BASELINE_ROW_MODELS.get(stem)
    if row_model is None:
        raise ValueError(f"Unsupported CoinTracking baseline export family: {stem}")
    return [
        row_model.model_validate(_normalize_blank_header(row)).to_row() for row in rows
    ]


def _normalize_blank_header(row: dict[str, str]) -> dict[str, str]:
    if "" not in row:
        return row
    unnamed_value = (row.get("") or "").strip()
    if unnamed_value:
        return row
    return {key: value for key, value in row.items() if key}
