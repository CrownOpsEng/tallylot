from __future__ import annotations

import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

import script_common


class ScriptCommonTests(unittest.TestCase):
    def test_require_directory_rejects_missing_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            missing = Path(tmpdir) / "missing"
            with self.assertRaises(FileNotFoundError):
                script_common.require_directory(missing, "Export directory")

    def test_require_directory_rejects_file_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "file.txt"
            path.write_text("x", encoding="utf-8")
            with self.assertRaises(NotADirectoryError):
                script_common.require_directory(path, "Export directory")

    def test_read_and_write_csv_rows_round_trip(self) -> None:
        rows = [{"filename": "a.csv", "size_bytes": 1, "sha256": "abc"}]
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "manifest.csv"
            script_common.write_csv_rows(path, ["filename", "size_bytes", "sha256"], rows)

            read_back = script_common.read_csv_rows(path)

        self.assertEqual([{"filename": "a.csv", "size_bytes": "1", "sha256": "abc"}], read_back)

    def test_read_csv_rows_accepts_utf8_bom(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "manifest.csv"
            path.write_text("\ufefffilename,size_bytes,sha256\na.csv,1,abc\n", encoding="utf-8")

            read_back = script_common.read_csv_rows(path)

        self.assertEqual([{"filename": "a.csv", "size_bytes": "1", "sha256": "abc"}], read_back)

    def test_write_csv_rows_creates_parent_directories(self) -> None:
        rows = [{"filename": "a.csv", "size_bytes": 1, "sha256": "abc"}]
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "nested" / "manifest.csv"
            script_common.write_csv_rows(path, ["filename", "size_bytes", "sha256"], rows)

            self.assertTrue(path.exists())

    def test_find_matching_csv_files_returns_sorted_csv_matches_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            export_dir = Path(tmpdir)
            (export_dir / "b Trade Table.csv").write_text("", encoding="utf-8")
            (export_dir / "a Trade Table.csv").write_text("", encoding="utf-8")
            (export_dir / "Trade Table.txt").write_text("", encoding="utf-8")

            matches = script_common.find_matching_csv_files(export_dir, "Trade Table")

        self.assertEqual(
            ["a Trade Table.csv", "b Trade Table.csv"],
            [path.name for path in matches],
        )

    def test_find_required_csv_exports_rejects_missing_required_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            export_dir = Path(tmpdir)
            (export_dir / "Current Balance.csv").write_text("", encoding="utf-8")

            with self.assertRaisesRegex(FileNotFoundError, "Trade Table"):
                script_common.find_required_csv_exports(
                    export_dir,
                    {"trade_table": "Trade Table", "current_balance": "Current Balance"},
                    "Export directory",
                )

    def test_find_required_csv_exports_rejects_ambiguous_match(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            export_dir = Path(tmpdir)
            (export_dir / "a Trade Table.csv").write_text("", encoding="utf-8")
            (export_dir / "b Trade Table.csv").write_text("", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Ambiguous export"):
                script_common.find_required_csv_exports(
                    export_dir,
                    {"trade_table": "Trade Table"},
                    "Export directory",
                )

    def test_find_required_csv_exports_returns_exact_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            export_dir = Path(tmpdir)
            trade = export_dir / "Trade Table.csv"
            balance = export_dir / "Current Balance.csv"
            trade.write_text("", encoding="utf-8")
            balance.write_text("", encoding="utf-8")

            files = script_common.find_required_csv_exports(
                export_dir,
                {"trade_table": "Trade Table", "current_balance": "Current Balance"},
                "Export directory",
            )

        self.assertEqual(trade.resolve(), files["trade_table"])
        self.assertEqual(balance.resolve(), files["current_balance"])

    def test_decimal_text_quantizes_to_eight_places(self) -> None:
        self.assertEqual("1.23456789", script_common.decimal_text(Decimal("1.234567891")))
        self.assertEqual("-0.00000001", script_common.decimal_text(Decimal("-0.00000001")))

    def test_write_json_creates_parent_directories_and_sorts_keys(self) -> None:
        payload = {"b": 2, "a": 1}
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "nested" / "summary.json"
            script_common.write_json(path, payload)

            text = path.read_text(encoding="utf-8")
            parsed = json.loads(text)

        self.assertTrue(text.endswith("\n"))
        self.assertLess(text.find('"a"'), text.find('"b"'))
        self.assertEqual(payload, parsed)

    def test_default_verification_exports_are_in_expected_order(self) -> None:
        self.assertEqual(
            [
                "Validate Transactions",
                "Missing Transactions",
                "Duplicate Transactions",
                "Current Balance",
                "Balance by Exchange",
            ],
            list(script_common.DEFAULT_VERIFICATION_EXPORTS),
        )
