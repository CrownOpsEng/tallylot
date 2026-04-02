from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pipeline_common


class PipelineCommonTests(unittest.TestCase):
    def test_manifest_fingerprint_is_order_independent(self) -> None:
        rows_a = [
            {"filename": "b.csv", "size_bytes": "2", "sha256": "bbb"},
            {"filename": "a.csv", "size_bytes": "1", "sha256": "aaa"},
        ]
        rows_b = list(reversed(rows_a))

        self.assertEqual(
            pipeline_common.manifest_fingerprint_from_rows(rows_a),
            pipeline_common.manifest_fingerprint_from_rows(rows_b),
        )

    def test_find_manifest_for_raw_dir_supports_capture_local_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_dir = Path(tmpdir) / "bsc-metamask1" / "2026-03"
            raw_dir.mkdir(parents=True)
            capture_manifest = raw_dir / "manifest.csv"
            capture_manifest.write_text("filename,size_bytes,sha256\n", encoding="utf-8")

            found = pipeline_common.find_manifest_for_raw_dir(raw_dir)

        self.assertEqual(capture_manifest, found)

    def test_build_file_inventory_classifies_known_csv_families(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_dir = Path(tmpdir)
            (raw_dir / "2026-03-23 Statement - All Time - account.csv").write_text(
                "Transactions\nID,Timestamp,Transaction Type\n",
                encoding="utf-8",
            )
            (raw_dir / "ledgerlive-operations.csv").write_text(
                "Operation Date,Status,Currency Ticker,Operation Type,Operation Amount\n",
                encoding="utf-8",
            )
            (raw_dir / "shakepay_Performance report_2025.pdf").write_bytes(b"%PDF-1.4\n")

            inventory = pipeline_common.build_file_inventory(raw_dir)

        by_name = {row["filename"]: row for row in inventory}
        self.assertEqual("custodial_all_time_csv", by_name["2026-03-23 Statement - All Time - account.csv"]["family"])
        self.assertEqual("wallet_operation_csv", by_name["ledgerlive-operations.csv"]["family"])
        self.assertEqual("statement_balance_pdf", by_name["shakepay_Performance report_2025.pdf"]["family"])

    def test_build_file_inventory_classifies_binance_specialized_families(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_dir = Path(tmpdir)
            (raw_dir / "Binance-Convert-Order-History-202603230441(UTC--6)_abcd.csv").write_text(
                "Time,Wallet,Pair,Type,Sell,Buy,Price,Inverse Price,Date Updated,Status\n",
                encoding="utf-8",
            )
            (raw_dir / "Binance-Fiat-Buy-History-202603230414(UTC--6)_abcd.csv").write_text(
                "Time,Method,Spend Amount,Receive Amount,Fee,Price,Status,Transaction ID\n",
                encoding="utf-8",
            )
            (raw_dir / "Binance-Deposit-History-202603230411(UTC--6)_abcd.csv").write_text(
                "Time,Coin,Network,Amount,Address,TXID,Status\n",
                encoding="utf-8",
            )

            inventory = pipeline_common.build_file_inventory(raw_dir)

        by_name = {row["filename"]: row for row in inventory}
        self.assertEqual("convert_order_csv", by_name["Binance-Convert-Order-History-202603230441(UTC--6)_abcd.csv"]["family"])
        self.assertEqual("fiat_buy_csv", by_name["Binance-Fiat-Buy-History-202603230414(UTC--6)_abcd.csv"]["family"])
        self.assertEqual("deposit_history_csv", by_name["Binance-Deposit-History-202603230411(UTC--6)_abcd.csv"]["family"])

    def test_parse_candidate_timestamp_accepts_two_digit_binance_year(self) -> None:
        parsed = pipeline_common.parse_candidate_timestamp("23-09-20 18:20:55")

        self.assertIsNotNone(parsed)
        self.assertEqual("2023-09-20 18:20:55", parsed.strftime("%Y-%m-%d %H:%M:%S"))

    def test_parse_candidate_timestamp_applies_source_timezone(self) -> None:
        parsed = pipeline_common.parse_candidate_timestamp(
            "23-09-20 18:20:55",
            source_timezone=pipeline_common.source_timezone_from_filename("Binance-Spot-Trade-History-202603230406(UTC--6)_5d63c10c.csv"),
        )

        self.assertIsNotNone(parsed)
        self.assertEqual("2023-09-21 00:20:55", parsed.strftime("%Y-%m-%d %H:%M:%S"))

    def test_build_file_inventory_converts_binance_filename_timezone_to_utc(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_dir = Path(tmpdir)
            (raw_dir / "Binance-Spot-Trade-History-202603230406(UTC--6)_abcd.csv").write_text(
                "Time,Pair,Side,Price,Executed,Amount,Fee\n"
                "23-09-20 18:20:55,ALGOUSDT,SELL,0.0997,103ALGO,10.2691USDT,0.00003593BNB\n",
                encoding="utf-8",
            )

            inventory = pipeline_common.build_file_inventory(raw_dir)

        row = inventory[0]
        self.assertEqual("2023-09-21 00:20:55", row["min_timestamp"])
        self.assertEqual("2023-09-21 00:20:55", row["max_timestamp"])
        self.assertEqual("filename_offset", row["timezone_mode"])
        self.assertEqual("UTC-06:00", row["timezone_value"])

    def test_build_file_inventory_detects_header_utc_and_date_only_modes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_dir = Path(tmpdir)
            (raw_dir / "crypto_transactions.csv").write_text(
                "Timestamp (UTC),Amount\n2021-07-06 17:37:09,1\n",
                encoding="utf-8",
            )
            (raw_dir / "activities-export.csv").write_text(
                "transaction_date,settlement_date,account_type\n2021-05-09,,Crypto\n",
                encoding="utf-8",
            )

            inventory = pipeline_common.build_file_inventory(raw_dir)

        by_name = {row["filename"]: row for row in inventory}
        self.assertEqual("header_utc", by_name["crypto_transactions.csv"]["timezone_mode"])
        self.assertEqual("UTC", by_name["crypto_transactions.csv"]["timezone_value"])
        self.assertEqual("date_only", by_name["activities-export.csv"]["timezone_mode"])
        self.assertEqual("date_only", by_name["activities-export.csv"]["timestamp_resolution"])

    def test_build_file_inventory_ignores_placeholder_no_data_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_dir = Path(tmpdir)
            (raw_dir / "Binance-Futures-Order-History-202603230503(UTC--6)_abcd.csv").write_text(
                "Uid,Time,Order No\nNo data matches the criteria.\n",
                encoding="utf-8",
            )

            inventory = pipeline_common.build_file_inventory(raw_dir)

        row = inventory[0]
        self.assertEqual("0", row["data_rows"])
        self.assertEqual("", row["date_field"])
        self.assertEqual("", row["timezone_mode"])

    def test_validate_canonical_event_row_requires_minimum_fields(self) -> None:
        row = {header: "" for header in pipeline_common.CANONICAL_EVENT_HEADERS}
        row.update(
            {
                "event_id": "evt-1",
                "source": "Coinbase",
                "timestamp": "2026-03-24 10:11:12",
                "event_kind": "Trade",
                "confidence": "high",
                "status": "mapped",
            }
        )
        pipeline_common.validate_canonical_event_row(row)

        row["event_id"] = ""
        with self.assertRaisesRegex(ValueError, "event_id"):
            pipeline_common.validate_canonical_event_row(row)
