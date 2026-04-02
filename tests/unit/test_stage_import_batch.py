from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import stage_import_batch
from tests.support.helpers import write_csv, read_json


class StageImportBatchTests(unittest.TestCase):
    def test_stage_import_batch_blocks_overlap_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            baseline = root / "baseline"
            baseline.mkdir()
            write_csv(
                baseline / "Trade Table.csv",
                ["Type", "Buy", "Cur.", "Sell", "Cur.", "Fee", "Cur.", "Exchange", "Group", "Comment", "Date", "Tx-ID"],
                [["Trade", "1.00000000", "BTC", "10.00000000", "CAD", "0.10000000", "CAD", "Coinbase", "", "", "2023-08-05 08:34:04", "tx-1"]],
            )
            candidate = root / "candidate.csv"
            write_csv(
                candidate,
                ["Type", "Buy", "Cur.", "Sell", "Cur.", "Fee", "Cur.", "Exchange", "Group", "Comment", "Date", "Tx-ID"],
                [["Trade", "1.00000000", "BTC", "10.00000000", "CAD", "0.10000000", "CAD", "Coinbase", "", "", "2023-08-05 08:34:04", "tx-1"]],
            )

            summary = stage_import_batch.stage_import_batch(candidate, baseline, root / "batch")
            self.assertEqual("blocked", summary["status"])
            self.assertEqual("UTC", summary["canonical_timezone"])
            self.assertEqual("UTC", summary["cointracking_import_timezone"])
            self.assertTrue((root / "batch" / "overlap_check" / "overlap_summary.json").exists())

    def test_stage_import_batch_stages_passing_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            baseline = root / "baseline"
            baseline.mkdir()
            write_csv(
                baseline / "Trade Table.csv",
                ["Type", "Buy", "Cur.", "Sell", "Cur.", "Fee", "Cur.", "Exchange", "Group", "Comment", "Date", "Tx-ID"],
                [["Trade", "1.00000000", "BTC", "10.00000000", "CAD", "0.10000000", "CAD", "Coinbase", "", "", "2023-08-05 08:34:04", "tx-1"]],
            )
            candidate = root / "candidate.csv"
            write_csv(
                candidate,
                ["Type", "Buy", "Cur.", "Sell", "Cur.", "Fee", "Cur.", "Exchange", "Group", "Comment", "Date", "Tx-ID"],
                [["Trade", "1.00000000", "BTC", "10.00000000", "CAD", "0.10000000", "CAD", "Coinbase", "", "", "2023-08-06 08:34:05", "tx-2"]],
            )

            summary = stage_import_batch.stage_import_batch(candidate, baseline, root / "batch", import_ready_dir=root / "ready")
            written = read_json(root / "batch" / "stage_summary.json")
            self.assertEqual("staged", summary["status"])
            self.assertEqual("UTC", summary["canonical_timezone"])
            self.assertEqual("UTC", summary["cointracking_import_timezone"])
            self.assertEqual(summary["staged_path"], written["staged_path"])
            self.assertTrue((root / "batch" / "candidate.csv").exists())
            self.assertTrue((root / "ready" / "candidate.csv").exists())

    def test_stage_import_batch_blocks_candidates_outside_normalization_window(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            baseline = root / "baseline"
            baseline.mkdir()
            write_csv(
                baseline / "Trade Table.csv",
                ["Type", "Buy", "Cur.", "Sell", "Cur.", "Fee", "Cur.", "Exchange", "Group", "Comment", "Date", "Tx-ID"],
                [["Trade", "1.00000000", "BTC", "10.00000000", "CAD", "0.10000000", "CAD", "Coinbase", "", "", "2023-08-05 08:34:04", "tx-1"]],
            )
            candidate = root / "candidate.csv"
            write_csv(
                candidate,
                ["Type", "Buy", "Cur.", "Sell", "Cur.", "Fee", "Cur.", "Exchange", "Group", "Comment", "Date", "Tx-ID"],
                [["Trade", "1.00000000", "BTC", "10.00000000", "CAD", "0.10000000", "CAD", "Coinbase", "", "", "2026-01-01 00:00:00", "tx-2"]],
            )

            summary = stage_import_batch.stage_import_batch(candidate, baseline, root / "batch")

            self.assertEqual("blocked", summary["status"])
            self.assertEqual(1, summary["rows_outside_normalization_window"])
