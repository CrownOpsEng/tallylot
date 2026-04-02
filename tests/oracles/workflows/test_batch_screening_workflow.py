from __future__ import annotations

import json
from pathlib import Path

from crypto_reconciliation.infrastructure.serialization.csv_io import write_rows
from crypto_reconciliation.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tools.oracles.contracts import ScreenBatchRequest
from tools.oracles.staging import BatchScreeningService


def test_batch_screening_writes_overlap_artifacts_for_review_required_candidates(
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
                "Type": "Trade",
                "Buy": "1.0",
                "Cur.": "BTC",
                "Sell": "10.0",
                "Cur..1": "CAD",
                "Fee": "0.1",
                "Cur..2": "CAD",
                "Exchange": "Fixture",
                "Group": "",
                "Comment": "overlap",
                "Date": "2023-08-05 08:34:04",
                "Tx-ID": "tx-1",
            },
        ),
    )
    output_dir = tmp_path / "screen"
    artifacts = FilesystemArtifactStore()

    response = BatchScreeningService(artifacts).execute(
        ScreenBatchRequest(
            candidate_path=candidate_path,
            baseline_export_dir=baseline_export_dir,
            output_dir=output_dir,
        )
    )

    overlap_summary = json.loads((output_dir / "overlap_check" / "overlap_summary.json").read_text(encoding="utf-8"))
    overlap_rows = artifacts.read_rows(output_dir / "overlap_check" / "overlap_flagged_rows.csv")

    assert response.passed is False
    assert response.overlap_rows_flagged == 1
    assert overlap_summary["status"] == "review_required"
    assert overlap_rows[0]["reasons"] == "on_or_before_cutoff;baseline_tx_id_match;baseline_economic_signature_match"


def test_batch_screening_surfaces_missing_required_candidate_fields(
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
                "Type": "Trade",
                "Buy": "1.0",
                "Cur.": "BTC",
                "Sell": "10.0",
                "Cur..1": "CAD",
                "Fee": "0.1",
                "Cur..2": "CAD",
                "Exchange": "Fixture",
                "Group": "",
                "Comment": "missing-date",
                "Date": "",
                "Tx-ID": "tx-2",
            },
            {
                "Type": "Trade",
                "Buy": "1.0",
                "Cur.": "BTC",
                "Sell": "10.0",
                "Cur..1": "CAD",
                "Fee": "0.1",
                "Cur..2": "CAD",
                "Exchange": "Fixture",
                "Group": "",
                "Comment": "missing-txid",
                "Date": "2023-08-06 10:00:00",
                "Tx-ID": "",
            },
        ),
    )
    output_dir = tmp_path / "screen"
    artifacts = FilesystemArtifactStore()

    response = BatchScreeningService(artifacts).execute(
        ScreenBatchRequest(
            candidate_path=candidate_path,
            baseline_export_dir=baseline_export_dir,
            output_dir=output_dir,
        )
    )

    issue_rows = artifacts.read_rows(output_dir / "stage_issues.csv")

    assert response.passed is False
    assert response.issue_count == 2
    assert [row["kind"] for row in issue_rows] == ["missing_date", "missing_tx_id"]


def test_batch_screening_surfaces_invalid_candidate_timestamps(
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
                "Comment": "invalid-date",
                "Date": "2023/08/06 10:00:00",
                "Tx-ID": "tx-2",
            },
        ),
    )
    output_dir = tmp_path / "screen"
    artifacts = FilesystemArtifactStore()

    response = BatchScreeningService(artifacts).execute(
        ScreenBatchRequest(
            candidate_path=candidate_path,
            baseline_export_dir=baseline_export_dir,
            output_dir=output_dir,
        )
    )

    issue_rows = artifacts.read_rows(output_dir / "stage_issues.csv")

    assert response.passed is False
    assert response.issue_count == 1
    assert issue_rows[0]["kind"] == "invalid_date"
