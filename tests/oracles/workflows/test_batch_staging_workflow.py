from __future__ import annotations

import json
from pathlib import Path

from crypto_reconciliation.infrastructure.serialization.csv_io import write_rows
from crypto_reconciliation.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tools.oracles.contracts import StageBatchRequest
from tools.oracles.staging import BatchScreeningService, BatchStagingService


def test_batch_staging_uses_normalization_summary_window_and_import_ready_copy(
    baseline_export_dir: Path,
    tmp_path: Path,
) -> None:
    normalized_dir = tmp_path / "normalized"
    normalized_dir.mkdir()
    candidate_path = normalized_dir / "candidate.csv"
    write_rows(
        candidate_path,
        (
            "Type",
            "Buy",
            "Cur.",
            "Sell",
            "Cur..1",
            "Fee",
            "Cur..2",
            "Exchange",
            "Group",
            "Comment",
            "Date",
            "Tx-ID",
        ),
        (
            {
                "Type": "trade",
                "Buy": "1.0",
                "Cur.": "BTC",
                "Sell": "10.0",
                "Cur..1": "CAD",
                "Fee": "0.1",
                "Cur..2": "CAD",
                "Exchange": "Fixture",
                "Group": "",
                "Comment": "window-ok",
                "Date": "2024-01-01 00:00:00",
                "Tx-ID": "tx-2",
            },
        ),
    )
    (normalized_dir / "normalization_summary.json").write_text(
        json.dumps(
            {
                "normalization_window_start": "2023-08-05 08:34:05",
                "normalization_window_end": "2024-12-31 23:59:59",
            }
        ),
        encoding="utf-8",
    )

    response = BatchStagingService(BatchScreeningService(FilesystemArtifactStore())).execute(
        StageBatchRequest(
            candidate_path=candidate_path,
            baseline_export_dir=baseline_export_dir,
            output_dir=tmp_path / "batch",
            import_ready_dir=tmp_path / "ready",
            staged_name="approved.csv",
        ),
    )

    summary = json.loads((tmp_path / "batch" / "stage_summary.json").read_text(encoding="utf-8"))

    assert response.staged is True
    assert response.staged_path == tmp_path / "batch" / "approved.csv"
    assert response.import_ready_copy_path == tmp_path / "ready" / "approved.csv"
    assert summary["normalization_summary"].endswith("normalization_summary.json")
    assert summary["rows_outside_normalization_window"] == 0


def test_batch_staging_explicit_window_overrides_normalization_summary(
    baseline_export_dir: Path,
    tmp_path: Path,
) -> None:
    normalized_dir = tmp_path / "normalized"
    normalized_dir.mkdir()
    candidate_path = normalized_dir / "candidate.csv"
    write_rows(
        candidate_path,
        (
            "Type",
            "Buy",
            "Cur.",
            "Sell",
            "Cur..1",
            "Fee",
            "Cur..2",
            "Exchange",
            "Group",
            "Comment",
            "Date",
            "Tx-ID",
        ),
        (
            {
                "Type": "trade",
                "Buy": "1.0",
                "Cur.": "BTC",
                "Sell": "10.0",
                "Cur..1": "CAD",
                "Fee": "0.1",
                "Cur..2": "CAD",
                "Exchange": "Fixture",
                "Group": "",
                "Comment": "window-override",
                "Date": "2024-01-01 00:00:00",
                "Tx-ID": "tx-2",
            },
        ),
    )
    (normalized_dir / "normalization_summary.json").write_text(
        json.dumps(
            {
                "normalization_window_start": "2023-08-05 08:34:05",
                "normalization_window_end": "2023-12-31 23:59:59",
            }
        ),
        encoding="utf-8",
    )

    response = BatchStagingService(BatchScreeningService(FilesystemArtifactStore())).execute(
        StageBatchRequest(
            candidate_path=candidate_path,
            baseline_export_dir=baseline_export_dir,
            output_dir=tmp_path / "batch",
            normalization_summary_path=normalized_dir / "normalization_summary.json",
            window_end="2024-12-31 23:59:59",
        ),
    )

    summary = json.loads((tmp_path / "batch" / "stage_summary.json").read_text(encoding="utf-8"))

    assert response.staged is True
    assert summary["normalization_window_end"] == "2024-12-31 23:59:59"
    assert summary["rows_outside_normalization_window"] == 0


def test_batch_staging_blocks_candidates_outside_normalization_window(
    baseline_export_dir: Path,
    tmp_path: Path,
) -> None:
    candidate_path = tmp_path / "candidate.csv"
    write_rows(
        candidate_path,
        (
            "Type",
            "Buy",
            "Cur.",
            "Sell",
            "Cur..1",
            "Fee",
            "Cur..2",
            "Exchange",
            "Group",
            "Comment",
            "Date",
            "Tx-ID",
        ),
        (
            {
                "Type": "trade",
                "Buy": "1.0",
                "Cur.": "BTC",
                "Sell": "10.0",
                "Cur..1": "CAD",
                "Fee": "0.1",
                "Cur..2": "CAD",
                "Exchange": "Fixture",
                "Group": "",
                "Comment": "too-late",
                "Date": "2026-01-01 00:00:00",
                "Tx-ID": "tx-2",
            },
        ),
    )

    response = BatchStagingService(BatchScreeningService(FilesystemArtifactStore())).execute(
        StageBatchRequest(
            candidate_path=candidate_path,
            baseline_export_dir=baseline_export_dir,
            output_dir=tmp_path / "batch",
        ),
    )

    summary = json.loads((tmp_path / "batch" / "stage_summary.json").read_text(encoding="utf-8"))

    assert response.staged is False
    assert "normalization_window_mismatch" in response.blocked_reason_codes
    assert summary["rows_outside_normalization_window"] == 1


def test_batch_staging_accepts_legacy_cointracking_currency_headers(
    baseline_export_dir: Path,
    tmp_path: Path,
) -> None:
    candidate_path = tmp_path / "candidate.csv"
    candidate_path.write_text(
        "Type,Buy,Cur.,Sell,Cur.,Fee,Cur.,Exchange,Group,Comment,Date,Tx-ID\n"
        "trade,1.0,BTC,10.0,CAD,0.1,CAD,Fixture,,legacy,2023-08-06 08:34:05,tx-2\n",
        encoding="utf-8",
    )

    response = BatchStagingService(BatchScreeningService(FilesystemArtifactStore())).execute(
        StageBatchRequest(
            candidate_path=candidate_path,
            baseline_export_dir=baseline_export_dir,
            output_dir=tmp_path / "batch",
        ),
    )

    assert response.staged is True
    assert response.staged_path == tmp_path / "batch" / "candidate.csv"
