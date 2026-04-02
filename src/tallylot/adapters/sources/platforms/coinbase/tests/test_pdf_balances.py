from __future__ import annotations

import pytest

from tallylot.adapters.sources.platforms.coinbase.pdf_balances import extract_pdf_balances


def test_coinbase_pdf_balances_extract_asset_rows() -> None:
    rows = extract_pdf_balances(
        """
        Coinbase Account Statement
        Portfolio summary balances are as of 2025-12-31 23:59:59 UTC
        BTC 1.2500 N/A 90000.00 CAD/BTC 112500.00 CAD
        ETH 2.5000 N/A 3000.00 CAD/ETH 7500.00 CAD
        """,
        "coinbase_statement.pdf",
    )

    assert len(rows) == 2
    assert rows[0]["source"] == "Coinbase"
    assert rows[0]["balance_kind"] == "asset_balance"
    assert rows[0]["asset"] == "BTC"
    assert rows[0]["quantity"] == "1.25"
    assert rows[0]["price_amount"] == "90000"
    assert rows[0]["value_amount"] == "112500.00"


def test_coinbase_pdf_balances_reject_empty_supported_statement() -> None:
    with pytest.raises(ValueError, match="no balance rows were extracted from the coinbase PDF"):
        extract_pdf_balances("Coinbase Account Statement", "statement.pdf")


def test_coinbase_pdf_balances_accepts_thousands_separators_in_prices() -> None:
    rows = extract_pdf_balances(
        """
        Coinbase Account Statement
        Portfolio summary balances are as of 2026-03-22 23:59:59 UTC
        ETH 0.001181807820874 N/A 2,817.007569 CAD/ETH 3.33 CAD
        """,
        "coinbase_statement.pdf",
    )

    assert len(rows) == 1
    assert rows[0]["asset"] == "ETH"
    assert rows[0]["price_amount"] == "2817.007569"
    assert rows[0]["value_amount"] == "3.33"


def test_coinbase_pdf_balances_extracts_closing_cash_when_as_of_precedes_amount() -> None:
    rows = extract_pdf_balances(
        """
        Coinbase Account Statement
        Closing Balance
        as of 2026-03-22 23:59:59 UTC
        0 CAD
        Portfolio summary balances are as of 2026-03-22 23:59:59 UTC
        ETH 0.001181807820874 N/A 2,817.007569 CAD/ETH 3.33 CAD
        """,
        "coinbase_statement.pdf",
    )

    assert len(rows) == 2
    assert rows[0]["balance_kind"] == "cash_closing_balance"
    assert rows[0]["asset"] == "CAD"
    assert rows[0]["quantity"] == "0"
    assert rows[0]["as_of"] == "2026-03-22 23:59:59"
