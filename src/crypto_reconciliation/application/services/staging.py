"""Import batch staging service."""

from __future__ import annotations

import shutil
from pathlib import Path

from crypto_reconciliation.application.dtos import StageBatchRequest, StageBatchResponse
from crypto_reconciliation.domain.value_objects import parse_timestamp
from crypto_reconciliation.ports.artifacts import ArtifactStorePort


class BatchStagingService:
    def __init__(self, artifacts: ArtifactStorePort) -> None:
        self._artifacts = artifacts

    def execute(self, request: StageBatchRequest) -> StageBatchResponse:
        request.output_dir.mkdir(parents=True, exist_ok=True)
        baseline_trade_table = _find_export(request.baseline_export_dir, "Trade Table")
        baseline_rows = self._artifacts.read_rows(baseline_trade_table)
        candidate_rows = self._artifacts.read_rows(request.candidate_path)

        baseline_cutoff = max(parse_timestamp(row["Date"]) for row in baseline_rows if row.get("Date"))
        baseline_tx_ids = {row.get("Tx-ID", "") for row in baseline_rows if row.get("Tx-ID")}
        duplicate_count = sum(1 for row in candidate_rows if row.get("Tx-ID", "") in baseline_tx_ids)
        has_time_overlap = any(
            parse_timestamp(row["Date"]) <= baseline_cutoff for row in candidate_rows if row.get("Date")
        )
        staged = duplicate_count == 0 and not has_time_overlap
        if staged:
            shutil.copy2(request.candidate_path, request.output_dir / request.candidate_path.name)
        self._artifacts.write_json(
            request.output_dir / "stage_summary.json",
            {
                "staged": staged,
                "duplicate_count": duplicate_count,
                "has_time_overlap": has_time_overlap,
                "candidate_rows": len(candidate_rows),
            },
        )
        return StageBatchResponse(
            output_dir=request.output_dir,
            staged=staged,
            duplicate_count=duplicate_count,
        )


def _find_export(export_dir: Path, stem: str) -> Path:
    matches = [path for path in export_dir.glob("*.csv") if stem.lower() in path.name.lower()]
    if len(matches) != 1:
        raise FileNotFoundError(f"expected exactly one export containing {stem!r} in {export_dir}")
    return matches[0]
