from __future__ import annotations

from pathlib import Path

import stage_import_batch
from tests.support.helpers import read_json, write_csv


def test_stage_import_batch_blocks_overlap_candidates(tmp_path: Path) -> None:
    root = tmp_path
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

    assert summary["status"] == "blocked"
    assert summary["canonical_timezone"] == "UTC"
    assert summary["cointracking_import_timezone"] == "UTC"
    assert (root / "batch" / "overlap_check" / "overlap_summary.json").exists()


def test_stage_import_batch_stages_passing_candidate(tmp_path: Path) -> None:
    root = tmp_path
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

    assert summary["status"] == "staged"
    assert summary["canonical_timezone"] == "UTC"
    assert summary["cointracking_import_timezone"] == "UTC"
    assert summary["staged_path"] == written["staged_path"]
    assert (root / "batch" / "candidate.csv").exists()
    assert (root / "ready" / "candidate.csv").exists()


def test_stage_import_batch_blocks_candidates_outside_normalization_window(tmp_path: Path) -> None:
    root = tmp_path
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

    assert summary["status"] == "blocked"
    assert summary["rows_outside_normalization_window"] == 1


def test_stage_import_batch_uses_normalization_summary_window_by_default(tmp_path: Path) -> None:
    root = tmp_path
    baseline = root / "baseline"
    baseline.mkdir()
    write_csv(
        baseline / "Trade Table.csv",
        ["Type", "Buy", "Cur.", "Sell", "Cur.", "Fee", "Cur.", "Exchange", "Group", "Comment", "Date", "Tx-ID"],
        [["Trade", "1.00000000", "BTC", "10.00000000", "CAD", "0.10000000", "CAD", "Coinbase", "", "", "2023-08-05 08:34:04", "tx-1"]],
    )
    normalized_dir = root / "normalized"
    normalized_dir.mkdir()
    candidate = normalized_dir / "candidate.csv"
    write_csv(
        candidate,
        ["Type", "Buy", "Cur.", "Sell", "Cur.", "Fee", "Cur.", "Exchange", "Group", "Comment", "Date", "Tx-ID"],
        [["Trade", "1.00000000", "BTC", "10.00000000", "CAD", "0.10000000", "CAD", "Coinbase", "", "", "2026-01-01 00:00:00", "tx-2"]],
    )
    (normalized_dir / "normalization_summary.json").write_text(
        (
            "{\n"
            '  "normalization_window_start": "2023-08-05 08:34:05",\n'
            '  "normalization_window_end": "2025-12-31 23:59:59"\n'
            "}\n"
        ),
        encoding="utf-8",
    )

    summary = stage_import_batch.stage_import_batch(candidate, baseline, root / "batch")

    assert summary["status"] == "blocked"
    assert summary["normalization_window_end"] == "2025-12-31 23:59:59"
    assert summary["normalization_summary"] == str((normalized_dir / "normalization_summary.json").resolve())
    assert summary["rows_outside_normalization_window"] == 1


def test_stage_import_batch_explicit_window_overrides_normalization_summary(tmp_path: Path) -> None:
    root = tmp_path
    baseline = root / "baseline"
    baseline.mkdir()
    write_csv(
        baseline / "Trade Table.csv",
        ["Type", "Buy", "Cur.", "Sell", "Cur.", "Fee", "Cur.", "Exchange", "Group", "Comment", "Date", "Tx-ID"],
        [["Trade", "1.00000000", "BTC", "10.00000000", "CAD", "0.10000000", "CAD", "Coinbase", "", "", "2023-08-05 08:34:04", "tx-1"]],
    )
    normalized_dir = root / "normalized"
    normalized_dir.mkdir()
    candidate = normalized_dir / "candidate.csv"
    write_csv(
        candidate,
        ["Type", "Buy", "Cur.", "Sell", "Cur.", "Fee", "Cur.", "Exchange", "Group", "Comment", "Date", "Tx-ID"],
        [["Trade", "1.00000000", "BTC", "10.00000000", "CAD", "0.10000000", "CAD", "Coinbase", "", "", "2024-01-01 00:00:00", "tx-2"]],
    )
    summary_path = normalized_dir / "normalization_summary.json"
    summary_path.write_text(
        (
            "{\n"
            '  "normalization_window_start": "2023-08-05 08:34:05",\n'
            '  "normalization_window_end": "2023-12-31 23:59:59"\n'
            "}\n"
        ),
        encoding="utf-8",
    )

    summary = stage_import_batch.stage_import_batch(
        candidate,
        baseline,
        root / "batch",
        normalization_summary=summary_path,
        window_end="2024-12-31 23:59:59",
    )

    assert summary["status"] == "staged"
    assert summary["normalization_window_end"] == "2024-12-31 23:59:59"
