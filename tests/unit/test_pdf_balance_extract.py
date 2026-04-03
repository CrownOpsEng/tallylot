from __future__ import annotations

import unittest
from pathlib import Path

import pdf_balance_extract


class PdfBalanceExtractTests(unittest.TestCase):
    def test_binance_balance_rows_from_text_extracts_total_and_wallets(self) -> None:
        text = """
        Report Period: January 01, 2025 - December 31, 2025
        Total Account Value: 0.43 USD
        Wallet Balance Funding Spot & Margin Futures Options Earn
        0.01 USD 0.42 USD 0.00 USD 0.00 USD 0.00 USD
        """

        rows = pdf_balance_extract.binance_balance_rows_from_text(text, "binance.pdf")

        self.assertEqual(6, len(rows))
        self.assertEqual("Consolidated", rows[0]["wallet"])
        self.assertEqual("Funding", rows[1]["wallet"])

    def test_shakepay_balance_rows_from_text_extracts_open_and_close(self) -> None:
        text = """
        Performance report For the year ending on December 31, 2025
        For the year ($) Since account opening ($) $256.37 $0.00
        Opening market value (as of 2025-01-01 00:00 EST)
        Closing market value at year end $643.81
        """

        rows = pdf_balance_extract.shakepay_balance_rows_from_text(text, "shakepay.pdf")

        self.assertEqual(2, len(rows))
        self.assertEqual("opening_market_value", rows[0]["balance_kind"])
        self.assertEqual("closing_market_value", rows[1]["balance_kind"])

    def test_detect_extractor_picks_known_filename_patterns(self) -> None:
        source, _ = pdf_balance_extract.detect_extractor(Path("binance.pdf"))
        self.assertEqual("binance", source)
