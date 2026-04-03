from __future__ import annotations

from tallylot.adapters.sources.platforms.binance.pdf_balances import extract_pdf_balances


def test_binance_pdf_balances_extract_total_and_wallet_breakdown() -> None:
    rows = extract_pdf_balances(
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
