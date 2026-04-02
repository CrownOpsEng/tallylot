"""Pydantic row models for CoinTracking baseline exports."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from tallylot.domain.value_objects import format_timestamp, parse_timestamp


class BaselineRowModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    _text_fields: ClassVar[tuple[str, ...]] = ()
    _decimal_fields: ClassVar[tuple[str, ...]] = ()
    _integer_fields: ClassVar[tuple[str, ...]] = ()
    _timestamp_fields: ClassVar[tuple[str, ...]] = ()
    _required_text_fields: ClassVar[tuple[str, ...]] = ()
    _required_decimal_fields: ClassVar[tuple[str, ...]] = ()
    _required_positive_integer_fields: ClassVar[tuple[str, ...]] = ()
    _required_timestamp_fields: ClassVar[tuple[str, ...]] = ()

    @field_validator("*", mode="before")
    @classmethod
    def _normalize_fields(cls, value: object, info: ValidationInfo) -> object:
        field_name = info.field_name or ""
        if field_name in cls._timestamp_fields:
            text = "" if value is None else str(value).strip()
            if field_name in cls._required_timestamp_fields and not text:
                raise ValueError(f"{field_name} must not be blank")
            if text:
                parse_timestamp(text)
            return text
        if field_name in cls._text_fields:
            text = "" if value is None else str(value).strip()
            if field_name in cls._required_text_fields and not text:
                raise ValueError(f"{field_name} must not be blank")
            return text
        if field_name in cls._decimal_fields:
            if value is None:
                if field_name in cls._required_decimal_fields:
                    raise ValueError(f"{field_name} must not be blank")
                return Decimal("0")
            if isinstance(value, Decimal):
                return value
            text = str(value).strip()
            if field_name in cls._required_decimal_fields and not text:
                raise ValueError(f"{field_name} must not be blank")
            return Decimal("0") if not text else Decimal(text)
        if field_name in cls._integer_fields:
            text = "" if value is None else str(value).strip()
            if field_name in cls._required_positive_integer_fields and not text:
                raise ValueError(f"{field_name} must not be blank")
            integer_value = 0 if not text else int(text)
            if (
                field_name in cls._required_positive_integer_fields
                and integer_value <= 0
            ):
                raise ValueError(f"{field_name} must be positive")
            return integer_value
        return value

    def to_row(self) -> dict[str, str]:
        return {
            alias: _row_text(value)
            for alias, value in self.model_dump(by_alias=True).items()
        }


class TradeTableRowModel(BaselineRowModel):
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
    _required_text_fields = ("trade_type", "exchange")
    _required_timestamp_fields = ("date",)

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


class CurrentBalanceRowModel(BaselineRowModel):
    _text_fields = ("ticker", "name", "asset_type")
    _decimal_fields = ("amount", "value_cad")
    _required_text_fields = ("ticker", "asset_type")
    _required_decimal_fields = ("amount", "value_cad")

    ticker: str = Field(alias="Ticker")
    name: str = Field(alias="Name")
    asset_type: str = Field(alias="Type")
    amount: Decimal = Field(alias="Amount")
    value_cad: Decimal = Field(alias="Value in CAD")


class BalanceByExchangeRowModel(BaselineRowModel):
    _text_fields = ("currency", "exchange")
    _decimal_fields = ("amount", "current_value_cad", "current_value_btc")
    _required_text_fields = ("currency", "exchange")
    _required_decimal_fields = ("amount", "current_value_cad", "current_value_btc")

    amount: Decimal = Field(alias="Amount")
    currency: str = Field(alias="Currency")
    current_value_cad: Decimal = Field(alias="Current value in CAD")
    current_value_btc: Decimal = Field(alias="Current value in BTC")
    exchange: str = Field(alias="Exchange")


class ValidateTransactionsRowModel(BaselineRowModel):
    _text_fields = ("issue",)
    _required_text_fields = ("issue",)

    issue: str = Field(alias="Issue")


class MissingTransactionsRowModel(BaselineRowModel):
    _text_fields = (
        "missing_type",
        "currency",
        "fee_currency",
        "exchange",
        "trade_group",
        "comment",
        "trade_id",
        "date",
        "match",
    )
    _decimal_fields = ("amount", "fee_amount", "value_cad")
    _timestamp_fields = ("date",)
    _required_text_fields = ("missing_type", "exchange")
    _required_decimal_fields = ("amount", "value_cad")

    missing_type: str = Field(alias="Type")
    amount: Decimal = Field(alias="Amount")
    currency: str = Field(alias="Cur.")
    fee_amount: Decimal = Field(alias="Fee")
    fee_currency: str = Field(alias="Fee Cur.")
    value_cad: Decimal = Field(alias="Value in CAD")
    exchange: str = Field(alias="Exchange")
    trade_group: str = Field(alias="Trade Group")
    comment: str = Field(alias="Comment")
    trade_id: str = Field(alias="Trade ID")
    date: str = Field(alias="Date")
    match: str = Field(alias="Match")


class DuplicateTransactionsRowModel(BaselineRowModel):
    _text_fields = (
        "duplicate_type",
        "exchange",
        "exchange_id",
        "buy",
        "sell",
        "trade_group",
        "transaction_id",
        "transaction_date",
    )
    _integer_fields = ("duplicate_count",)
    _timestamp_fields = ("transaction_date",)
    _required_text_fields = ("duplicate_type", "exchange")
    _required_positive_integer_fields = ("duplicate_count",)
    _required_timestamp_fields = ("transaction_date",)

    duplicate_count: int = Field(alias="# of duplicates")
    duplicate_type: str = Field(alias="Type")
    exchange: str = Field(alias="Exchange")
    exchange_id: str = Field(alias="Exchange ID")
    buy: str = Field(alias="Buy")
    sell: str = Field(alias="Sell")
    trade_group: str = Field(alias="Trade Group")
    transaction_id: str = Field(alias="Tx ID")
    transaction_date: str = Field(alias="Tx Date")


def _row_text(value: object) -> str:
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return format_timestamp(value)
    return "" if value is None else str(value)
