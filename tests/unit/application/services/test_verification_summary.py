from __future__ import annotations

from collections import Counter
from decimal import Decimal

from crypto_reconciliation.application.services.verification import (
    build_balance_map,
    build_exchange_balance_map,
    compare_balance_maps,
    compare_exchange_balance_maps,
    decimal_text,
    expand_counter_delta,
    row_counter,
    subtract_counters,
)


def test_decimal_text_quantizes_to_eight_places() -> None:
    assert decimal_text(Decimal("1.234567891")) == "1.23456789"


def test_row_counter_and_expand_counter_delta_preserve_duplicate_rows() -> None:
    rows = [
        {"Issue": "one"},
        {"Issue": "one"},
        {"Issue": "two"},
    ]

    delta = expand_counter_delta(subtract_counters(row_counter(rows), Counter()))

    assert delta == [
        {"Issue": "one"},
        {"Issue": "one"},
        {"Issue": "two"},
    ]


def test_build_balance_map_aggregates_by_ticker() -> None:
    rows = [
        {"Ticker": "BTC", "Amount": "1.0"},
        {"Ticker": "BTC", "Amount": "0.5"},
        {"Ticker": "ETH", "Amount": "2.0"},
    ]

    assert build_balance_map(rows) == {"BTC": Decimal("1.5"), "ETH": Decimal("2.0")}


def test_build_exchange_balance_map_aggregates_by_exchange_and_currency() -> None:
    rows = [
        {"Exchange": "Coinbase", "Currency": "BTC", "Amount": "1.0"},
        {"Exchange": "Coinbase", "Currency": "BTC", "Amount": "0.5"},
        {"Exchange": "Binance", "Currency": "ETH", "Amount": "2.0"},
    ]

    assert build_exchange_balance_map(rows) == {
        ("Coinbase", "BTC"): Decimal("1.5"),
        ("Binance", "ETH"): Decimal("2.0"),
    }


def test_compare_balance_maps_reports_asset_deltas() -> None:
    rows = compare_balance_maps(
        previous={"BTC": Decimal("1.0")},
        current={"BTC": Decimal("1.5"), "ETH": Decimal("2.0")},
    )

    assert rows == [
        {
            "ticker": "BTC",
            "reference_amount": "1.00000000",
            "current_amount": "1.50000000",
            "difference": "0.50000000",
        },
        {
            "ticker": "ETH",
            "reference_amount": "0.00000000",
            "current_amount": "2.00000000",
            "difference": "2.00000000",
        },
    ]


def test_compare_exchange_balance_maps_reports_exchange_deltas() -> None:
    rows = compare_exchange_balance_maps(
        previous={("Coinbase", "BTC"): Decimal("1.0")},
        current={
            ("Coinbase", "BTC"): Decimal("1.5"),
            ("Binance", "ETH"): Decimal("2.0"),
        },
    )

    assert rows == [
        {
            "exchange": "Binance",
            "currency": "ETH",
            "reference_amount": "0.00000000",
            "current_amount": "2.00000000",
            "difference": "2.00000000",
        },
        {
            "exchange": "Coinbase",
            "currency": "BTC",
            "reference_amount": "1.00000000",
            "current_amount": "1.50000000",
            "difference": "0.50000000",
        },
    ]
