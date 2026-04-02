from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from tests.support.helpers import read_dict_rows, write_csv
import baseline_check
import script_common


class BaselineCheckUnitTests(unittest.TestCase):
    def test_find_required_files_rejects_missing_required_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            export_dir = Path(tmpdir)
            write_csv(
                export_dir / "Trade Table.csv",
                ["Type", "Buy", "Cur.", "Sell", "Cur.", "Fee", "Cur.", "Exchange", "Group", "Comment", "Date"],
                [["Trade", "1", "BTC", "10", "CAD", "0", "CAD", "X", "", "", "2023-08-05 08:34:04"]],
            )
            for marker in [
                "Current Balance",
                "Validate Transactions",
                "Missing Transactions",
                "Duplicate Transactions",
            ]:
                write_csv(export_dir / f"{marker}.csv", ["A"], [["1"]])

            with self.assertRaisesRegex(FileNotFoundError, "Balance by Exchange"):
                baseline_check.find_required_files(export_dir)

    def test_find_required_files_rejects_ambiguous_match(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            export_dir = Path(tmpdir)
            write_csv(
                export_dir / "a Trade Table.csv",
                ["Type", "Buy", "Cur.", "Sell", "Cur.", "Fee", "Cur.", "Exchange", "Group", "Comment", "Date"],
                [["Trade", "1", "BTC", "10", "CAD", "0", "CAD", "X", "", "", "2023-08-05 08:34:04"]],
            )
            write_csv(
                export_dir / "b Trade Table.csv",
                ["Type", "Buy", "Cur.", "Sell", "Cur.", "Fee", "Cur.", "Exchange", "Group", "Comment", "Date"],
                [["Trade", "1", "BTC", "10", "CAD", "0", "CAD", "X", "", "", "2023-08-05 08:34:04"]],
            )
            for marker in [
                "Current Balance",
                "Balance by Exchange",
                "Validate Transactions",
                "Missing Transactions",
                "Duplicate Transactions",
            ]:
                write_csv(export_dir / f"{marker}.csv", ["A"], [["1"]])

            with self.assertRaisesRegex(ValueError, "Ambiguous export"):
                baseline_check.find_required_files(export_dir)

    def test_decimal_text_quantizes_to_eight_places(self) -> None:
        self.assertEqual("1.23456789", baseline_check.decimal_text(Decimal("1.234567891")))
        self.assertEqual("-0.00000001", baseline_check.decimal_text(Decimal("-0.00000001")))

    def test_find_required_files_uses_shared_helper_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            export_dir = Path(tmpdir)
            for marker in baseline_check.REQUIRED_FILES.values():
                write_csv(export_dir / f"{marker}.csv", ["A"], [["1"]])

            self.assertEqual(
                script_common.find_required_csv_exports(export_dir, baseline_check.REQUIRED_FILES, "Export directory"),
                baseline_check.find_required_files(export_dir),
            )

    def test_parse_trade_table_row_treats_blank_numeric_fields_as_zero(self) -> None:
        parsed = baseline_check.parse_trade_table_row(
            ["Trade", "", "BTC", "", "CAD", "", "CAD", "X", "", "", "2023-08-05 08:34:04"]
        )

        self.assertEqual(
            ("Trade", Decimal("0"), "BTC", Decimal("0"), "CAD", Decimal("0"), "CAD"),
            parsed,
        )

    def test_build_asset_snapshot_sorts_and_tracks_negative_balances(self) -> None:
        rows = [
            {"Ticker": "BTC", "Name": "Bitcoin", "Type": "Coin", "Amount": "1.50000000", "Value in CAD": "100000"},
            {"Ticker": "CAD", "Name": "Canadian Dollar", "Type": "Currency", "Amount": "-12.34000000", "Value in CAD": "-12.34"},
        ]

        snapshot_rows, current_by_ticker, negative_balances = baseline_check.build_asset_snapshot(rows)

        self.assertEqual(["BTC", "CAD"], [row["ticker"] for row in snapshot_rows])
        self.assertEqual(Decimal("1.50000000"), current_by_ticker["BTC"])
        self.assertEqual("CAD", negative_balances[0]["ticker"])
        self.assertEqual("-12.34000000", negative_balances[0]["amount"])

    def test_build_exchange_reconciliation_detects_drift_and_cad_rows(self) -> None:
        current_by_ticker = {"BTC": Decimal("1.0"), "CAD": Decimal("-5.0")}
        exchange_rows = [
            {"Amount": "0.4", "Currency": "BTC", "Current value in CAD": "1", "Exchange": "A"},
            {"Amount": "0.7", "Currency": "BTC", "Current value in CAD": "2", "Exchange": "B"},
            {"Amount": "-5.0", "Currency": "CAD", "Current value in CAD": "-5", "Exchange": "Bank"},
        ]

        reconciliation_rows, cad_rows, max_difference, max_ticker = baseline_check.build_exchange_reconciliation(
            current_by_ticker,
            exchange_rows,
        )

        btc_row = next(row for row in reconciliation_rows if row["ticker"] == "BTC")
        self.assertEqual("drift", btc_row["status"])
        self.assertEqual("0.10000000", btc_row["difference"])
        self.assertEqual("Bank", cad_rows[0]["exchange"])
        self.assertEqual(Decimal("0.1"), max_difference)
        self.assertEqual("BTC", max_ticker)

    def test_build_exchange_reconciliation_includes_extra_exchange_only_assets(self) -> None:
        reconciliation_rows, cad_rows, max_difference, max_ticker = baseline_check.build_exchange_reconciliation(
            {"BTC": Decimal("1.0")},
            [{"Amount": "2.0", "Currency": "ETH", "Current value in CAD": "5000", "Exchange": "Wallet"}],
        )

        eth_row = next(row for row in reconciliation_rows if row["ticker"] == "ETH")
        self.assertEqual("0.00000000", eth_row["current_balance_amount"])
        self.assertEqual("2.00000000", eth_row["balance_by_exchange_amount"])
        self.assertEqual("2.00000000", eth_row["difference"])
        self.assertEqual("drift", eth_row["status"])
        self.assertEqual([], cad_rows)
        self.assertEqual(Decimal("2.0"), max_difference)
        self.assertEqual("ETH", max_ticker)

    def test_build_source_activity_merges_trade_and_balance_views(self) -> None:
        rows = baseline_check.build_source_activity(
            [
                {"Exchange": "Wallet A", "Date": "2023-08-01 00:00:00"},
                {"Exchange": "Wallet A", "Date": "2023-08-05 08:34:04"},
                {"Exchange": "Wallet B", "Date": "2023-08-03 00:00:00"},
            ],
            [
                {"Exchange": "Wallet A", "Currency": "BTC"},
                {"Exchange": "Wallet A", "Currency": "ETH"},
                {"Exchange": "Wallet C", "Currency": "ADA"},
            ],
        )

        wallet_a = next(row for row in rows if row["source"] == "Wallet A")
        wallet_c = next(row for row in rows if row["source"] == "Wallet C")

        self.assertEqual("2023-08-01 00:00:00", wallet_a["first_trade_timestamp"])
        self.assertEqual("2023-08-05 08:34:04", wallet_a["last_trade_timestamp"])
        self.assertEqual("2", wallet_a["trade_table_rows"])
        self.assertEqual("2", wallet_a["balance_asset_count"])
        self.assertEqual("yes", wallet_a["present_in_trade_table"])
        self.assertEqual("yes", wallet_a["present_in_balance_by_exchange"])
        self.assertEqual("", wallet_c["first_trade_timestamp"])
        self.assertEqual("0", wallet_c["trade_table_rows"])
        self.assertEqual("1", wallet_c["balance_by_exchange_rows"])
        self.assertEqual("no", wallet_c["present_in_trade_table"])
        self.assertEqual("yes", wallet_c["present_in_balance_by_exchange"])

    def test_build_cad_flow_summary_aggregates_by_type(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            trade_table = Path(tmpdir) / "trade_table.csv"
            write_csv(
                trade_table,
                ["Type", "Buy", "Cur.", "Sell", "Cur.", "Fee", "Cur.", "Exchange", "Group", "Comment", "Date"],
                [
                    ["Trade", "100.00", "CAD", "1.0", "BTC", "2.00", "CAD", "X", "", "", "2024-01-01 00:00:00"],
                    ["Trade", "0.5", "BTC", "50.00", "CAD", "0.50", "CAD", "X", "", "", "2024-01-02 00:00:00"],
                    ["Income", "25.00", "CAD", "0", "", "0", "", "X", "", "", "2024-01-03 00:00:00"],
                ],
            )

            cad_flow_rows, cad_bought_total, cad_sold_total, cad_fee_total = baseline_check.build_cad_flow_summary(
                trade_table
            )

        self.assertEqual(Decimal("125.00"), cad_bought_total)
        self.assertEqual(Decimal("50.00"), cad_sold_total)
        self.assertEqual(Decimal("2.50"), cad_fee_total)
        trade_row = next(row for row in cad_flow_rows if row["type"] == "Trade")
        self.assertEqual("100.00000000", trade_row["cad_bought"])
        self.assertEqual("50.00000000", trade_row["cad_sold"])

    def test_build_cad_flow_summary_returns_zero_totals_without_cad_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            trade_table = Path(tmpdir) / "trade_table.csv"
            write_csv(
                trade_table,
                ["Type", "Buy", "Cur.", "Sell", "Cur.", "Fee", "Cur.", "Exchange", "Group", "Comment", "Date"],
                [["Trade", "1.0", "BTC", "2.0", "ETH", "0.01", "BTC", "X", "", "", "2024-01-01 00:00:00"]],
            )

            cad_flow_rows, cad_bought_total, cad_sold_total, cad_fee_total = baseline_check.build_cad_flow_summary(
                trade_table
            )

        self.assertEqual([], cad_flow_rows)
        self.assertEqual(Decimal("0"), cad_bought_total)
        self.assertEqual(Decimal("0"), cad_sold_total)
        self.assertEqual(Decimal("0"), cad_fee_total)

    def test_build_baseline_artifacts_from_minimal_export_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            export_dir = Path(tmpdir)
            write_csv(
                export_dir / "Trade Table.csv",
                ["Type", "Buy", "Cur.", "Sell", "Cur.", "Fee", "Cur.", "Exchange", "Group", "Comment", "Date"],
                [["Trade", "1.0", "BTC", "10.0", "CAD", "0.5", "CAD", "Coinbase", "", "", "2023-08-05 08:34:04"]],
            )
            write_csv(
                export_dir / "Current Balance.csv",
                ["Ticker", "Name", "Type", "Amount", "Value in CAD"],
                [["BTC", "Bitcoin", "Coin", "1.00000000", "10.00"], ["CAD", "Canadian Dollar", "Currency", "-10.00000000", "-10.00"]],
            )
            write_csv(
                export_dir / "Balance by Exchange.csv",
                ["Amount", "Currency", "Current value in CAD", "Current value in BTC", "Exchange"],
                [["1.00000000", "BTC", "10.00", "0.1", "Coinbase"], ["-10.00000000", "CAD", "-10.00", "-0.1", "Coinbase"]],
            )
            write_csv(export_dir / "Validate Transactions.csv", ["Issue"], [["AXS"]])
            write_csv(export_dir / "Missing Transactions.csv", ["Issue"], [["Missing"]])
            write_csv(export_dir / "Duplicate Transactions.csv", ["Issue"], [])

            artifacts = baseline_check.build_baseline_artifacts(export_dir)

        self.assertEqual("2023-08-05 08:34:04", artifacts["summary"]["latest_transaction_timestamp"])
        self.assertEqual(2, artifacts["summary"]["current_balance_rows"])
        self.assertEqual(1, artifacts["summary"]["negative_balance_rows"])
        self.assertEqual("0.00000000", artifacts["summary"]["max_asset_difference"])
        self.assertEqual("", artifacts["summary"]["max_asset_difference_ticker"])
        self.assertEqual("-10.00000000", artifacts["summary"]["ending_cad_balance"])
        self.assertEqual("0.00000000", artifacts["summary"]["cad_bought_total"])
        self.assertEqual("10.00000000", artifacts["summary"]["cad_sold_total"])
        self.assertEqual("0.50000000", artifacts["summary"]["cad_fee_total"])
        self.assertEqual(2, artifacts["summary"]["asset_reconciliation_assets"])
        self.assertEqual(1, artifacts["summary"]["trade_table_sources"])
        self.assertEqual(1, artifacts["summary"]["balance_by_exchange_sources"])
        self.assertEqual(1, artifacts["summary"]["source_activity_rows"])
        self.assertEqual(
            [
                {
                    "ticker": "CAD",
                    "name": "Canadian Dollar",
                    "type": "Currency",
                    "amount": "-10.00000000",
                    "value_cad": "-10.00",
                }
            ],
            artifacts["negative_balances"],
        )

    def test_latest_trade_timestamp_requires_dated_rows(self) -> None:
        with self.assertRaisesRegex(ValueError, "did not contain any dated rows"):
            baseline_check.latest_trade_timestamp([{"Date": ""}])

    def test_latest_trade_timestamp_returns_latest_row(self) -> None:
        latest = baseline_check.latest_trade_timestamp(
            [
                {"Date": "2023-08-05 08:33:00"},
                {"Date": "2023-08-05 08:34:04"},
                {"Date": "2023-08-05 08:34:03"},
            ]
        )

        self.assertEqual("2023-08-05 08:34:04", latest.strftime("%Y-%m-%d %H:%M:%S"))

    def test_latest_trade_timestamp_rejects_malformed_timestamp(self) -> None:
        with self.assertRaises(ValueError):
            baseline_check.latest_trade_timestamp([{"Date": "2023/08/05 08:34:04"}])

    def test_parse_trade_table_row_rejects_short_rows(self) -> None:
        with self.assertRaisesRegex(ValueError, "too short"):
            baseline_check.parse_trade_table_row(["Trade", "1"])


class BaselineCheckWriteArtifactsTests(unittest.TestCase):
    def test_write_baseline_artifacts_creates_expected_files(self) -> None:
        artifacts = {
            "asset_snapshot_rows": [{"ticker": "BTC", "name": "Bitcoin", "type": "Coin", "amount": "1.0", "value_cad": "1"}],
            "reconciliation_rows": [
                {
                    "ticker": "BTC",
                    "current_balance_amount": "1.0",
                    "balance_by_exchange_amount": "1.0",
                    "difference": "0.0",
                    "status": "match",
                }
            ],
            "negative_balances": [],
            "source_activity_rows": [
                {
                    "source": "Wallet",
                    "first_trade_timestamp": "2023-08-05 08:34:04",
                    "last_trade_timestamp": "2023-08-05 08:34:04",
                    "trade_table_rows": "1",
                    "balance_by_exchange_rows": "1",
                    "balance_asset_count": "1",
                    "present_in_trade_table": "yes",
                    "present_in_balance_by_exchange": "yes",
                }
            ],
            "cad_flow_rows": [],
            "cad_balance_by_exchange_rows": [],
            "summary": {"latest_transaction_timestamp": "2023-08-05 08:34:04"},
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir)
            baseline_check.write_baseline_artifacts(out_dir, artifacts)

            produced = sorted(path.name for path in out_dir.iterdir())
            self.assertEqual(
                [
                    "baseline_asset_snapshot.csv",
                    "baseline_cad_balance_by_exchange.csv",
                    "baseline_cad_flow_by_type.csv",
                    "baseline_exchange_reconciliation.csv",
                    "baseline_negative_balances.csv",
                    "baseline_source_activity.csv",
                    "baseline_summary.json",
                ],
                produced,
            )
            with (out_dir / "baseline_summary.json").open(encoding="utf-8") as handle:
                self.assertEqual("2023-08-05 08:34:04", json.load(handle)["latest_transaction_timestamp"])
            self.assertEqual(
                [{"ticker": "BTC", "name": "Bitcoin", "type": "Coin", "amount": "1.0", "value_cad": "1"}],
                read_dict_rows(out_dir / "baseline_asset_snapshot.csv"),
            )
            self.assertEqual(
                [
                    {
                        "ticker": "BTC",
                        "current_balance_amount": "1.0",
                        "balance_by_exchange_amount": "1.0",
                        "difference": "0.0",
                        "status": "match",
                    }
                ],
                read_dict_rows(out_dir / "baseline_exchange_reconciliation.csv"),
            )


class BaselineCheckCliUnitTests(unittest.TestCase):
    def test_parse_args_reads_expected_paths(self) -> None:
        args = baseline_check.parse_args(["--export-dir", "exports", "--out-dir", "out"])

        self.assertEqual(Path("exports"), args.export_dir)
        self.assertEqual(Path("out"), args.out_dir)

    def test_main_writes_artifacts_and_prints_summary_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            export_dir = Path(tmpdir) / "exports"
            out_dir = Path(tmpdir) / "out"
            export_dir.mkdir()
            write_csv(
                export_dir / "Trade Table.csv",
                ["Type", "Buy", "Cur.", "Sell", "Cur.", "Fee", "Cur.", "Exchange", "Group", "Comment", "Date"],
                [["Trade", "1.0", "BTC", "10.0", "CAD", "0.5", "CAD", "Coinbase", "", "", "2023-08-05 08:34:04"]],
            )
            write_csv(
                export_dir / "Current Balance.csv",
                ["Ticker", "Name", "Type", "Amount", "Value in CAD"],
                [["BTC", "Bitcoin", "Coin", "1.00000000", "10.00"], ["CAD", "Canadian Dollar", "Currency", "-10.00000000", "-10.00"]],
            )
            write_csv(
                export_dir / "Balance by Exchange.csv",
                ["Amount", "Currency", "Current value in CAD", "Current value in BTC", "Exchange"],
                [["1.00000000", "BTC", "10.00", "0.1", "Coinbase"], ["-10.00000000", "CAD", "-10.00", "-0.1", "Coinbase"]],
            )
            write_csv(export_dir / "Validate Transactions.csv", ["Issue"], [["AXS"]])
            write_csv(export_dir / "Missing Transactions.csv", ["Issue"], [["Missing"]])
            write_csv(export_dir / "Duplicate Transactions.csv", ["Issue"], [])

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = baseline_check.main(["--export-dir", str(export_dir), "--out-dir", str(out_dir)])

            summary = json.loads(stdout.getvalue())
            summary_exists = (out_dir / "baseline_summary.json").exists()

        self.assertEqual(0, exit_code)
        self.assertEqual("2023-08-05 08:34:04", summary["latest_transaction_timestamp"])
        self.assertTrue(summary_exists)
