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

