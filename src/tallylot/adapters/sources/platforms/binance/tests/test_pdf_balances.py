from __future__ import annotations

from tallylot.adapters.sources.platforms.binance.pdf_balances import (
    extract_pdf_balances,
)


def test_binance_pdf_balances_extract_structured_holdings_rows() -> None:
    rows = extract_pdf_balances(
        """
        Report Date: 2026/03/23
        Asset Allocation Your Consolidated Top 10 Assets
        Symbol Quantity (Beginning Value / Change) Price (Beginning Value / Change) Value (Beginning Value / Change) (USD)
        SOLO Sologenic 0.920099 0.920099 / 0.000000 $0.177402 $0.177402 / $0.000000 $0.16 $0.16 / $0.00
        Funding Top 10 Holdings
        Symbol Quantity (Beginning Value / Change) Price (Beginning Value / Change) Value (Beginning Value / Change) (USD)
        USDT TetherUS 0.009526 0.009526 / 0.000000 $1.000000 $1.000000 / $0.000000 $0.01 $0.01 / $0.00
        Spot Top 10 Holdings
        Symbol Quantity (Beginning Value / Change) Price (Beginning Value / Change) Value (Beginning Value / Change) (USD)
        SOLO Sologenic 0.920099 0.920099 / 0.000000 $0.177402 $0.177402 / $0.000000 $0.16 $0.16 / $0.00
        USDT TetherUS 0.000340 0.000340 / 0.000000 $1.000000 $1.000000 / $0.000000 $0.00 $0.00 / $0.00
        """,
        "binance.pdf",
    )

    assert len(rows) == 3
    assert rows[0]["wallet"] == "Funding"
    assert rows[0]["asset"] == "USDT"
    assert rows[0]["quantity"] == "0.009526"
    assert rows[0]["as_of"] == "2026-03-23"
    assert rows[1]["wallet"] == "Spot"
    assert rows[1]["asset"] == "SOLO"
    assert rows[2]["asset"] == "USDT"


def test_binance_pdf_balances_reject_total_value_only_rows() -> None:
    rows = extract_pdf_balances(
        """
        Report Date: 2026/03/23
        Total Account Value: 0.35 USD
        Wallet Balance
        Funding
        0.01 USD
        """,
        "binance.pdf",
    )

    assert rows == []
