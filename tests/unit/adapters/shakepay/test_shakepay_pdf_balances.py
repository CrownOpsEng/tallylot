from __future__ import annotations

from crypto_reconciliation.adapters.sources.platforms.shakepay.pdf_balances import extract_pdf_balances


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
    assert rows[1]["as_of"] == "2025-12-31 23:59"
