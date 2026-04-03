from __future__ import annotations

import pytest

from crypto_reconciliation.adapters.sources.coinbase.pdf_balances import extract_pdf_balances


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
