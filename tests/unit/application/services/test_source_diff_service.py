from __future__ import annotations

import json
from pathlib import Path

from crypto_reconciliation.application.models.source import SourceDiffRequest
from crypto_reconciliation.application.services.source_diff import SourceDiffService
from crypto_reconciliation.infrastructure.serialization.csv_io import write_rows
from crypto_reconciliation.infrastructure.serialization.filesystem import FilesystemArtifactStore


def test_source_reconciliation_service_writes_candidate_and_reference_diffs(tmp_path: Path) -> None:
    candidate_path = tmp_path / "candidate.csv"
    reference_path = tmp_path / "reference.csv"
    header = ("Type", "Date", "Tx-ID")
    write_rows(
        candidate_path,
        header,
        (
            {"Type": "Trade", "Date": "2023-08-06 10:00:00", "Tx-ID": "tx-1"},
            {"Type": "Trade", "Date": "2023-08-07 10:00:00", "Tx-ID": "tx-2"},
        ),
    )
    write_rows(
        reference_path,
        header,
        (
            {"Type": "Trade", "Date": "2023-08-06 10:00:00", "Tx-ID": "tx-1"},
            {"Type": "Trade", "Date": "2023-08-08 10:00:00", "Tx-ID": "tx-3"},
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
    duplicate_row = {"Type": "Trade", "Date": "2024-01-01 00:00:00", "Tx-ID": "dup"}
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
