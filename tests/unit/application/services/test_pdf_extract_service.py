from __future__ import annotations

from pathlib import Path

import pytest

from crypto_reconciliation.application.services.pdf_extract import (
    _binance_rows,
    _detect_statement_kind,
    _parse_balance_lines,
    _shakepay_rows,
)


def test_detect_statement_kind_accepts_requested_supported_kind() -> None:
    assert _detect_statement_kind(Path("anything.pdf"), "anything", "binance") == "binance"


def test_detect_statement_kind_rejects_unknown_requested_kind() -> None:
    with pytest.raises(ValueError, match="unsupported statement kind"):
        _detect_statement_kind(Path("anything.pdf"), "anything", "kraken")


def test_detect_statement_kind_rejects_unknown_pdf_text() -> None:
    with pytest.raises(ValueError, match="unable to detect supported statement kind"):
        _detect_statement_kind(Path("statement.pdf"), "Generic account export", None)


def test_detect_statement_kind_uses_filename_patterns_without_text_hints() -> None:
    assert _detect_statement_kind(Path("binance.pdf"), "", None) == "binance"
    assert _detect_statement_kind(Path("shakepay_Performance report_2025.pdf"), "", None) == "shakepay"


def test_parse_balance_lines_rejects_empty_supported_statement() -> None:
    with pytest.raises(ValueError, match="no balance rows were extracted"):
        _parse_balance_lines("Coinbase Account Statement", "coinbase", "statement.pdf")


def test_binance_rows_extract_total_and_wallet_breakdown() -> None:
    rows = _binance_rows(
        """
        Report Period: January 01, 2025 - December 31, 2025
        Total Account Value: 0.43 USD
        Wallet Balance Funding Spot & Margin Futures Options Earn
        0.01 USD 0.42 USD 0.00 USD 0.00 USD 0.00 USD
        """,
        "binance.pdf",
    )

    assert len(rows) == 6
    assert rows[0]["wallet"] == "Consolidated"
    assert rows[0]["value_amount"] == "0.43"
    assert rows[1]["wallet"] == "Funding"
    assert rows[2]["wallet"] == "Spot & Margin"


def test_shakepay_rows_extract_opening_and_closing_market_values() -> None:
    rows = _shakepay_rows(
        """
        Performance report For the year ending on December 31, 2025
        For the year ($) Since account opening ($) $256.37 $0.00
        Opening market value (as of 2025-01-01 00:00 EST)
        Closing market value at year end $643.81
        """,
        "shakepay.pdf",
    )

    assert len(rows) == 2
    assert rows[0]["balance_kind"] == "opening_market_value"
    assert rows[0]["as_of"] == "2025-01-01 00:00 EST"
    assert rows[1]["balance_kind"] == "closing_market_value"
    assert rows[1]["as_of"] == "2025-12-31 23:59"
