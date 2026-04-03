from __future__ import annotations

from tallylot.adapters.sources.platforms.shakepay.pdf_balances import extract_pdf_balances


def test_shakepay_pdf_balances_extract_opening_and_closing_market_values() -> None:
    rows = extract_pdf_balances(
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
    assert rows[1]["as_of"] == "2025-12-31 23:59 EST"


def test_shakepay_pdf_balances_extracts_values_from_live_layout() -> None:
    rows = extract_pdf_balances(
        """
        Performance report For the year ending on December 31, 2025
        Change in value of your account For the year ($) Since account opening ($)
        Opening market value $256.37 $0.00 (as of 2025-01-01 00:00 EST)
        Debit -$11,778.94 -$17,694.29
        Closing market value at year end $643.81 $643.81 (as of 2025-12-31 23:59 EST)
        """,
        "shakepay.pdf",
    )

    assert len(rows) == 2
    assert rows[0]["value_amount"] == "256.37"
    assert rows[0]["as_of"] == "2025-01-01 00:00 EST"
    assert rows[1]["value_amount"] == "643.81"
    assert rows[1]["as_of"] == "2025-12-31 23:59 EST"
