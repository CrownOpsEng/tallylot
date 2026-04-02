from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from tests.support.helpers import read_dict_rows, write_csv
import overlap_check


class OverlapCheckTests(unittest.TestCase):
    def test_find_trade_table_rejects_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            export_dir = Path(tmpdir)
            with self.assertRaisesRegex(FileNotFoundError, "Trade Table"):
                overlap_check.find_trade_table(export_dir)

    def test_find_trade_table_rejects_ambiguous_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            export_dir = Path(tmpdir)
            write_csv(export_dir / "a Trade Table.csv", ["Type", "Date"], [])
            write_csv(export_dir / "b Trade Table.csv", ["Type", "Date"], [])

            with self.assertRaisesRegex(ValueError, "Ambiguous export"):
                overlap_check.find_trade_table(export_dir)

    def test_parse_datetime_accepts_both_supported_formats(self) -> None:
        self.assertEqual("2023-08-05 08:34:04", overlap_check.parse_datetime("2023-08-05 08:34:04").strftime("%Y-%m-%d %H:%M:%S"))
        self.assertEqual("2023-08-05 08:34:04", overlap_check.parse_datetime("05.08.2023 08:34:04").strftime("%Y-%m-%d %H:%M:%S"))

    def test_build_cointracking_column_map_accepts_alternate_headers(self) -> None:
        columns = overlap_check.build_cointracking_column_map(
            ["Type", "Buy", "Cur.", "Sell", "Cur.", "Fee", "Cur.", "Exchange", "Trade Group", "Comment", "Trade Date", "Transaction ID"]
        )

        self.assertIsNotNone(columns["group"])
        self.assertIsNotNone(columns["date"])
        self.assertIsNotNone(columns["tx_id"])

    def test_build_cointracking_column_map_requires_type_and_date(self) -> None:
        with self.assertRaisesRegex(ValueError, "Type' and 'Date"):
            overlap_check.build_cointracking_column_map(["Buy", "Cur.", "Sell", "Cur."])

    def test_summarize_overlap_flags_cutoff_and_signature_matches(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            export_dir = Path(tmpdir) / "baseline"
            export_dir.mkdir()
            candidate = Path(tmpdir) / "candidate.csv"
            write_csv(
                export_dir / "Trade Table.csv",
                ["Type", "Buy", "Cur.", "Sell", "Cur.", "Fee", "Cur.", "Exchange", "Group", "Comment", "Date", "LPN", "Tx-ID"],
                [
                    ["Trade", "1.0", "BTC", "10.0", "CAD", "0.5", "CAD", "Coinbase", "", "", "2023-08-05 08:34:04", "", "tx-1"],
                    ["Trade", "2.0", "ETH", "20.0", "CAD", "0.1", "CAD", "Coinbase", "", "", "2023-08-05 08:35:04", "", "tx-2"],
                ],
            )
            write_csv(
                candidate,
                ["Type", "Buy", "Cur.", "Sell", "Cur.", "Fee", "Cur.", "Exchange", "Group", "Comment", "Date", "Tx-ID"],
                [
                    ["Trade", "1.0", "BTC", "10.0", "CAD", "0.5", "CAD", "Coinbase", "", "", "2023-08-05 08:34:04", "tx-1"],
                    ["Trade", "3.0", "SOL", "30.0", "CAD", "0.2", "CAD", "Coinbase", "", "", "2023-08-05 08:36:04", "tx-3"],
                ],
            )

            summary, flagged_rows = overlap_check.summarize_overlap(export_dir, candidate)

        self.assertEqual("2023-08-05 08:35:04", summary["cutoff_timestamp"])
        self.assertEqual(2, summary["candidate_row_count"])
        self.assertEqual(1, summary["rows_flagged"])
        self.assertEqual(1, summary["rows_on_or_before_cutoff"])
        self.assertEqual(1, summary["rows_with_baseline_tx_id_match"])
        self.assertEqual(1, summary["rows_with_baseline_economic_signature_match"])
        self.assertEqual("review_required", summary["status"])
        self.assertEqual("2", flagged_rows[0]["row_number"])
        self.assertIn("baseline_tx_id_match", flagged_rows[0]["reasons"])

    def test_summarize_overlap_flags_blank_and_unparseable_dates(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            export_dir = Path(tmpdir) / "baseline"
            export_dir.mkdir()
            candidate = Path(tmpdir) / "candidate.csv"
            write_csv(
                export_dir / "Trade Table.csv",
                ["Type", "Buy", "Cur.", "Sell", "Cur.", "Fee", "Cur.", "Exchange", "Group", "Comment", "Date", "LPN", "Tx-ID"],
                [["Trade", "1.0", "BTC", "10.0", "CAD", "0.5", "CAD", "Coinbase", "", "", "2023-08-05 08:34:04", "", "tx-1"]],
            )
            write_csv(
                candidate,
                ["Type", "Buy", "Cur.", "Sell", "Cur.", "Fee", "Cur.", "Exchange", "Group", "Comment", "Date", "Tx-ID"],
                [
                    ["Trade", "2.0", "ETH", "20.0", "CAD", "0.1", "CAD", "Coinbase", "", "", "", "tx-2"],
                    ["Trade", "3.0", "SOL", "30.0", "CAD", "0.2", "CAD", "Coinbase", "", "", "2023/08/05 08:35:04", "tx-3"],
                ],
            )

            summary, flagged_rows = overlap_check.summarize_overlap(export_dir, candidate)

        self.assertEqual(2, summary["rows_flagged"])
        self.assertEqual(1, summary["rows_with_blank_date"])
        self.assertEqual(1, summary["rows_with_unparseable_date"])
        self.assertEqual(["blank_date", "unparseable_date"], [row["reasons"] for row in flagged_rows])

    def test_write_overlap_artifacts_writes_summary_and_csv(self) -> None:
        summary = {"status": "pass"}
        flagged_rows = [
            {
                "row_number": "2",
                "reasons": "on_or_before_cutoff",
                "type": "Trade",
                "buy": "1",
                "buy_currency": "BTC",
                "sell": "10",
                "sell_currency": "CAD",
                "fee": "0",
                "fee_currency": "CAD",
                "exchange": "Coinbase",
                "date": "2023-08-05 08:34:04",
                "tx_id": "tx-1",
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir)
            overlap_check.write_overlap_artifacts(out_dir, summary, flagged_rows)

            with (out_dir / "overlap_summary.json").open(encoding="utf-8") as handle:
                written_summary = json.load(handle)
            written_rows = read_dict_rows(out_dir / "overlap_flagged_rows.csv")

        self.assertEqual("pass", written_summary["status"])
        self.assertEqual("tx-1", written_rows[0]["tx_id"])

    def test_main_prints_summary_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            export_dir = Path(tmpdir) / "baseline"
            export_dir.mkdir()
            candidate = Path(tmpdir) / "candidate.csv"
            out_dir = Path(tmpdir) / "out"
            write_csv(
                export_dir / "Trade Table.csv",
                ["Type", "Buy", "Cur.", "Sell", "Cur.", "Fee", "Cur.", "Exchange", "Group", "Comment", "Date", "LPN", "Tx-ID"],
                [["Trade", "1.0", "BTC", "10.0", "CAD", "0.5", "CAD", "Coinbase", "", "", "2023-08-05 08:34:04", "", "tx-1"]],
            )
            write_csv(
                candidate,
                ["Type", "Buy", "Cur.", "Sell", "Cur.", "Fee", "Cur.", "Exchange", "Group", "Comment", "Date", "Tx-ID"],
                [["Trade", "2.0", "ETH", "20.0", "CAD", "0.1", "CAD", "Coinbase", "", "", "2023-08-05 08:35:04", "tx-2"]],
            )

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                exit_code = overlap_check.main(
                    [
                        "--baseline-export-dir",
                        str(export_dir),
                        "--candidate",
                        str(candidate),
                        "--out-dir",
                        str(out_dir),
                    ]
                )

            summary = json.loads(stdout.getvalue())
            summary_exists = (out_dir / "overlap_summary.json").exists()

        self.assertEqual(0, exit_code)
        self.assertEqual("pass", summary["status"])
        self.assertTrue(summary_exists)
