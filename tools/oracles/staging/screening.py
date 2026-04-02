"""Batch screening workflow."""

from __future__ import annotations

from pathlib import Path

from crypto_reconciliation.ports.artifacts import ArtifactStorePort
from tools.oracles.cointracking.screening import screen_candidate
from tools.oracles.contracts import ScreenBatchRequest, ScreenBatchResponse, ScreeningResult

from .constants import ISSUE_HEADER, NORMALIZED_TIMEZONE, OUTPUT_IMPORT_TIMEZONE
from .overlap_artifacts import summary_int, write_overlap_artifacts


class BatchScreeningService:
    def __init__(self, artifacts: ArtifactStorePort) -> None:
        self._artifacts = artifacts

    @property
    def artifacts(self) -> ArtifactStorePort:
        return self._artifacts

    def execute(self, request: ScreenBatchRequest) -> ScreenBatchResponse:
        request.output_dir.mkdir(parents=True, exist_ok=True)
        screening = self._screen(request.candidate_path, request.baseline_export_dir)
        if screening.overlap_result is not None:
            write_overlap_artifacts(
                request.output_dir / "overlap_check",
                screening.overlap_result,
                write_json=self._artifacts.write_json,
                write_rows=self._artifacts.write_rows,
            )
        self._artifacts.write_rows(
            request.output_dir / "stage_issues.csv",
            ISSUE_HEADER,
            (issue.to_row() for issue in screening.issues),
        )
        self._artifacts.write_json(
            request.output_dir / "stage_summary.json",
            {
                "passed": screening.passed,
                "duplicate_count": screening.duplicate_count,
                "has_time_overlap": screening.has_time_overlap,
                "candidate_rows": screening.candidate_rows,
                "issue_count": len(screening.issues),
                "overlap_rows_flagged": (
                    0
                    if screening.overlap_result is None
                    else summary_int(screening.overlap_result.summary, "rows_flagged")
                ),
                "normalized_timezone": NORMALIZED_TIMEZONE,
                "output_import_timezone": OUTPUT_IMPORT_TIMEZONE,
                "blocked_reason_codes": list(screening.blocked_reason_codes),
            },
        )
        return ScreenBatchResponse(
            output_dir=request.output_dir,
            passed=screening.passed,
            duplicate_count=screening.duplicate_count,
            has_time_overlap=screening.has_time_overlap,
            candidate_rows=screening.candidate_rows,
            issue_count=len(screening.issues),
            blocked_reason_codes=screening.blocked_reason_codes,
            overlap_rows_flagged=(
                0 if screening.overlap_result is None else summary_int(screening.overlap_result.summary, "rows_flagged")
            ),
        )

    def _screen(self, candidate_path: Path, baseline_export_dir: Path) -> ScreeningResult:
        return screen_candidate(candidate_path, baseline_export_dir, self._artifacts)
