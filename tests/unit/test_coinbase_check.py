from __future__ import annotations

import unittest

import coinbase_check


def expected_row(**overrides: str) -> dict[str, str]:
    row = {
        "Type": "Trade",
        "Buy": "0.00175640",
        "Buy Cur.": "BTC",
        "Sell": "25.00000000",
        "Sell Cur.": "CAD",
        "Fee": "1.46965254",
        "Fee Cur.": "CAD",
        "Exchange": "Coinbase",
        "Group": "",
        "Comment": "Bought 0.0017564 BTC for $25.00 CAD",
        "Date": "2019-09-11 01:06:35",
        "Tx-ID": "coinbase-retail-buy-1",
        "match_window_seconds": "20",
        "fee_tolerance": "0.03000000",
        "comment_mode": "exact",
        "tx_id_mode": "ignore",
        "allowed_types": "Trade",
        "raw_source": "coinbase.csv",
        "raw_ref": "buy-1",
        "notes": "",
    }
    row.update(overrides)
    return row


def actual_row(**overrides: str) -> dict[str, str]:
    row = {
        "Type": "Trade",
        "Buy": "0.00175640",
        "Buy Cur.": "BTC",
        "Sell": "25.00000000",
        "Sell Cur.": "CAD",
        "Fee": "1.49000000",
        "Fee Cur.": "CAD",
        "Exchange": "Coinbase",
        "Group": "",
        "Comment": "Bought 0.0017564 BTC for $25.00 CAD",
        "Date": "2019-09-11 01:06:26",
        "Tx-ID": "",
    }
    row.update(overrides)
    return row


class CoinbaseCheckTests(unittest.TestCase):
    def test_compare_transactions_flags_extra_synthetic_row(self) -> None:
        expected = [expected_row()]
        actual = [
            actual_row(),
            {
                "Type": "Deposit",
                "Buy": "25.00000000",
                "Buy Cur.": "CAD",
                "Sell": "",
                "Sell Cur.": "",
                "Fee": "0.00000000",
                "Fee Cur.": "",
                "Exchange": "Coinbase",
                "Group": "",
                "Comment": "",
                "Date": "2019-09-11 01:06:26",
                "Tx-ID": "",
            },
        ]

        results = coinbase_check.compare_transactions(actual, expected)

        self.assertEqual(1, len(results["matched"]))
        self.assertEqual(1, len(results["extra"]))
        self.assertEqual("Deposit", results["extra"][0]["Type"])

    def test_compare_transactions_flags_fee_mismatch_even_when_type_is_allowed_variant(self) -> None:
        expected = [
            expected_row(
                Type="Withdrawal",
                Buy="",
                **{
                    "Buy Cur.": "",
                    "Sell": "0.05516500",
                    "Sell Cur.": "ETH",
                    "Fee": "0.00000000",
                    "Fee Cur.": "ETH",
                    "Comment": "Sent 0.055165 ETH to 0xabc",
                    "Date": "2019-10-30 00:38:57",
                    "fee_tolerance": "0.00000000",
                    "comment_mode": "ignore",
                    "allowed_types": "Withdrawal|Spend",
                },
            )
        ]
        actual = [
            actual_row(
                Type="Spend",
                Buy="",
                **{
                    "Buy Cur.": "",
                    "Sell": "0.05516500",
                    "Sell Cur.": "ETH",
                    "Fee": "0.00021000",
                    "Fee Cur.": "ETH",
                    "Comment": "Sent 0.055165 ETH to 0xabc",
                    "Date": "2019-10-30 00:38:57",
                },
            )
        ]

        results = coinbase_check.compare_transactions(actual, expected)

        self.assertEqual(1, len(results["mismatched"]))
        self.assertEqual("fee_mismatch", results["mismatched"][0]["comparison_issues"])

    def test_compare_balances_reports_asset_deltas(self) -> None:
        deltas = coinbase_check.compare_balances(
            [
                {"Amount": "1.00000000", "Currency": "BTC", "Exchange": "Coinbase"},
                {"Amount": "0.50000000", "Currency": "ETH", "Exchange": "Coinbase"},
            ],
            [
                {"source": "Coinbase", "balance_kind": "asset_balance", "asset": "BTC", "quantity": "1.00000000"},
                {"source": "Coinbase", "balance_kind": "asset_balance", "asset": "ETH", "quantity": "0.40000000"},
            ],
        )

        eth_row = next(row for row in deltas if row["asset"] == "ETH")
        self.assertEqual("delta", eth_row["status"])
        self.assertEqual("0.10000000", eth_row["difference"])
