from __future__ import annotations

import json
from pathlib import Path

from tallylot.infrastructure.serialization.csv_io import write_rows
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tools.oracles.contracts import SourceDiffRequest
from tools.oracles.source_diff import SourceDiffService


def test_source_reconciliation_service_writes_candidate_and_reference_diffs(tmp_path: Path) -> None:
    candidate_path = tmp_path / "candidate.csv"
    reference_path = tmp_path / "reference.csv"
    header = ("Type", "Date", "Tx-ID")
    write_rows(
        candidate_path,
        header,
        (
            {"Type": "trade", "Date": "2023-08-06 10:00:00", "Tx-ID": "tx-1"},
            {"Type": "trade", "Date": "2023-08-07 10:00:00", "Tx-ID": "tx-2"},
        ),
    )
    write_rows(
        reference_path,
        header,
        (
            {"Type": "trade", "Date": "2023-08-06 10:00:00", "Tx-ID": "tx-1"},
            {"Type": "trade", "Date": "2023-08-08 10:00:00", "Tx-ID": "tx-3"},
        ),
    )
    output_dir = tmp_path / "reconcile"

    response = SourceDiffService(FilesystemArtifactStore()).execute(
        SourceDiffRequest(candidate_path=candidate_path, reference_path=reference_path, output_dir=output_dir)
    )

    summary = json.loads((output_dir / "diff_summary.json").read_text(encoding="utf-8"))

    assert response.candidate_only_count == 1
    assert response.reference_only_count == 1
    assert response.matched_count == 1
    assert summary["matched_count"] == 1
    assert (output_dir / "candidate_only.csv").exists()
    assert (output_dir / "reference_only.csv").exists()


def test_source_reconciliation_service_preserves_duplicate_row_multiplicity(tmp_path: Path) -> None:
    candidate_path = tmp_path / "candidate.csv"
    reference_path = tmp_path / "reference.csv"
    output_dir = tmp_path / "reconcile"
    header = ("Type", "Date", "Tx-ID")
    duplicate_row = {"Type": "trade", "Date": "2024-01-01 00:00:00", "Tx-ID": "dup"}
    write_rows(candidate_path, header, (duplicate_row, duplicate_row))
    write_rows(reference_path, header, (duplicate_row,))

    response = SourceDiffService(FilesystemArtifactStore()).execute(
        SourceDiffRequest(candidate_path=candidate_path, reference_path=reference_path, output_dir=output_dir)
    )

    candidate_only_rows = FilesystemArtifactStore().read_rows(output_dir / "candidate_only.csv")

    assert response.candidate_only_count == 1
    assert response.reference_only_count == 0
    assert response.matched_count == 1
    assert candidate_only_rows == [duplicate_row]


def test_source_reconciliation_service_handles_mismatched_candidate_and_reference_headers(tmp_path: Path) -> None:
    candidate_path = tmp_path / "candidate.csv"
    reference_path = tmp_path / "reference.csv"
    output_dir = tmp_path / "reconcile"
    write_rows(candidate_path, ("Type", "Date", "Tx-ID"), ({"Type": "trade", "Date": "2024-01-01", "Tx-ID": "tx-1"},))
    write_rows(
        reference_path,
        ("Type", "Trade Date", "Trade Group", "Tx Hash"),
        ({"Type": "trade", "Trade Date": "2024-01-01", "Trade Group": "spot", "Tx Hash": "hash-1"},),
    )

    response = SourceDiffService(FilesystemArtifactStore()).execute(
        SourceDiffRequest(candidate_path=candidate_path, reference_path=reference_path, output_dir=output_dir)
    )

    reference_only_rows = FilesystemArtifactStore().read_rows(output_dir / "reference_only.csv")

    assert response.candidate_only_count == 1
    assert response.reference_only_count == 1
    assert response.matched_count == 0
    assert reference_only_rows == [
        {
            "Type": "trade",
            "Date": "",
            "Tx-ID": "",
            "Trade Date": "2024-01-01",
            "Trade Group": "spot",
            "Tx Hash": "hash-1",
        }
    ]
