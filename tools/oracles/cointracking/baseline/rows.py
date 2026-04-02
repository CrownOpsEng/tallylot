"""Typed CoinTracking baseline export row models."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

from tallylot.domain.value_objects import parse_timestamp
from tallylot.ports.artifacts import ArtifactStorePort


class _BaselineRowModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    _text_fields: ClassVar[tuple[str, ...]] = ()
    _decimal_fields: ClassVar[tuple[str, ...]] = ()
    _timestamp_fields: ClassVar[tuple[str, ...]] = ()

    @field_validator("*", mode="before")
    @classmethod
    def _normalize_fields(cls, value: object, info: object) -> object:
        field_name = getattr(info, "field_name", "")
        if field_name in cls._timestamp_fields:
            text = "" if value is None else str(value).strip()
            if text:
                parse_timestamp(text)
            return text
        if field_name in cls._text_fields:
            return "" if value is None else str(value).strip()
        if field_name in cls._decimal_fields:
            if value is None:
                return Decimal("0")
            if isinstance(value, Decimal):
                return value
            text = str(value).strip()
            return Decimal("0") if not text else Decimal(text)
        return value

    def to_row(self) -> dict[str, str]:
        return {
            alias: _row_text(value)
            for alias, value in self.model_dump(by_alias=True).items()
        }


class TradeTableRowModel(_BaselineRowModel):
    _text_fields = (
        "trade_type",
        "buy_currency",
        "sell_currency",
        "fee_currency",
        "exchange",
        "group",
        "comment",
        "date",
        "transaction_id",
    )
    _decimal_fields = ("buy_amount", "sell_amount", "fee_amount")
    _timestamp_fields = ("date",)

    trade_type: str = Field(alias="Type")
    buy_amount: Decimal = Field(alias="Buy")
    buy_currency: str = Field(alias="Cur.")
    sell_amount: Decimal = Field(alias="Sell")
    sell_currency: str = Field(alias="Cur..1")
    fee_amount: Decimal = Field(alias="Fee")
    fee_currency: str = Field(alias="Cur..2")
    exchange: str = Field(alias="Exchange")
    group: str = Field(alias="Group")
    comment: str = Field(alias="Comment")
    date: str = Field(alias="Date")
    transaction_id: str = Field(alias="Tx-ID")


class CurrentBalanceRowModel(_BaselineRowModel):
    _text_fields = ("ticker", "name", "asset_type", "value_cad")
    _decimal_fields = ("amount",)

    ticker: str = Field(alias="Ticker")
    name: str = Field(alias="Name")
    asset_type: str = Field(alias="Type")
    amount: Decimal = Field(alias="Amount")
    value_cad: str = Field(alias="Value in CAD")


class BalanceByExchangeRowModel(_BaselineRowModel):
    _text_fields = ("currency", "current_value_cad", "current_value_btc", "exchange")
    _decimal_fields = ("amount",)

    amount: Decimal = Field(alias="Amount")
    currency: str = Field(alias="Currency")
    current_value_cad: str = Field(alias="Current value in CAD")
    current_value_btc: str = Field(alias="Current value in BTC")
    exchange: str = Field(alias="Exchange")


class ValidateTransactionsRowModel(_BaselineRowModel):
    _text_fields = ("issue",)

    issue: str = Field(alias="Issue")


class MissingTransactionsRowModel(_BaselineRowModel):
    _text_fields = (
        "missing_type",
        "currency",
        "fee_currency",
        "value_cad",
        "exchange",
        "trade_group",
        "comment",
        "trade_id",
        "date",
        "match",
    )
    _decimal_fields = ("amount", "fee_amount")
    _timestamp_fields = ("date",)

    missing_type: str = Field(alias="Type")
    amount: Decimal = Field(alias="Amount")
    currency: str = Field(alias="Cur.")
    fee_amount: Decimal = Field(alias="Fee")
    fee_currency: str = Field(alias="Fee Cur.")
    value_cad: str = Field(alias="Value in CAD")
    exchange: str = Field(alias="Exchange")
    trade_group: str = Field(alias="Trade Group")
    comment: str = Field(alias="Comment")
    trade_id: str = Field(alias="Trade ID")
    date: str = Field(alias="Date")
    match: str = Field(alias="Match")


class DuplicateTransactionsRowModel(_BaselineRowModel):
    _text_fields = (
        "duplicate_count",
        "duplicate_type",
        "exchange",
        "exchange_id",
        "buy",
        "sell",
        "trade_group",
        "transaction_id",
        "transaction_date",
    )
    _timestamp_fields = ("transaction_date",)

    duplicate_count: str = Field(alias="# of duplicates")
    duplicate_type: str = Field(alias="Type")
    exchange: str = Field(alias="Exchange")
    exchange_id: str = Field(alias="Exchange ID")
    buy: str = Field(alias="Buy")
    sell: str = Field(alias="Sell")
    trade_group: str = Field(alias="Trade Group")
    transaction_id: str = Field(alias="Tx ID")
    transaction_date: str = Field(alias="Tx Date")


_BASELINE_ROW_MODELS: dict[str, type[_BaselineRowModel]] = {
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
    row_model = _BASELINE_ROW_MODELS[stem]
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


def _row_text(value: object) -> str:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return "" if value is None else str(value)
