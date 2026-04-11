from __future__ import annotations

from pathlib import Path

from tallylot.adapters.sources.platforms.shakepay.pdf_balances import (
    extract_pdf_balances,
    match_statement_document,
)


def test_shakepay_pdf_balances_extract_monthly_balance_summary_rows() -> None:
    rows = extract_pdf_balances(
        """
        Monthly account statement
        Balance summary (as of 2026-04-01 00:00 EDT)
        Asset Quantity* Market price (CA$) Market value (CA$)** Original cost (CA$)***
        Cash (CAD) 18.76 1.00 18.76 18.76
        US Dollar (USD) 0.00 1.3911 0.00 0.00
        Bitcoin (BTC) 0.00186458 94,692.31 176.56 261.71
        Ethereum (ETH) 0.00020245 2,922.49 0.59 0.51
        """,
        "shakepay_2026-03.pdf",
    )

    assert len(rows) == 4
    assert rows[0]["balance_kind"] == "available"
    assert rows[0]["asset"] == "CAD"
    assert rows[0]["quantity"] == "18.76"
    assert rows[0]["as_of"] == "2026-04-01 04:00:00"
    assert rows[-1]["asset"] == "ETH"
    assert rows[-1]["quantity"] == "0.00020245"


def test_shakepay_pdf_balances_extracts_annual_market_value_report() -> None:
    text = """
        Performance report For the year ending on December 31, 2025
        Opening market value $256.37 $0.00 (as of 2025-01-01 00:00 EST)
        Closing market value at year end $643.81 $643.81 (as of 2025-12-31 23:59 EST)
        """
    rows = extract_pdf_balances(
        text,
        "shakepay.pdf",
    )

    assert (
        match_statement_document(Path("shakepay_Performance report_2025.pdf"), text) > 0
    )
    assert len(rows) == 2
    assert rows[0]["balance_kind"] == "opening_market_value"
    assert rows[0]["value_amount"] == "256.37"
    assert rows[0]["as_of"] == "2025-01-01 00:00 EST"
    assert rows[1]["balance_kind"] == "closing_market_value"
    assert rows[1]["value_amount"] == "643.81"
    assert rows[1]["as_of"] == "2025-12-31 23:59 EST"
