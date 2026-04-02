from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.infrastructure.serialization.csv_io import write_rows
from crypto_reconciliation.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tools.oracles.contracts import StageBatchRequest
from tools.oracles.staging import BatchScreeningService, BatchStagingService


def test_batch_staging_detects_duplicates(
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
                "Comment": "dup",
                "Date": "2023-08-06 10:00:00",
                "Tx-ID": "tx-1",
            },
        ),
    )
    artifacts = FilesystemArtifactStore()

    response = BatchStagingService(BatchScreeningService(artifacts)).execute(
        StageBatchRequest(
            candidate_path=candidate_path,
            baseline_export_dir=baseline_export_dir,
            output_dir=tmp_path / "batch",
        ),
    )

    assert response.staged is False
    assert response.duplicate_count == 1
