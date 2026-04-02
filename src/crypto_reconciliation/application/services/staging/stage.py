"""Batch staging workflow."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import cast

from crypto_reconciliation.application.models.batch import ScreenBatchRequest, StageBatchRequest, StageBatchResponse
from crypto_reconciliation.domain.types import JsonValue

from .constants import NORMALIZED_TIMEZONE, OUTPUT_IMPORT_TIMEZONE
from .screening import BatchScreeningService
from .windows import count_candidate_rows_outside_window, resolve_normalization_window


class BatchStagingService:
    def __init__(self, screening: BatchScreeningService) -> None:
        self._screening = screening

    def execute(self, request: StageBatchRequest) -> StageBatchResponse:
        response = self._screening.execute(
            ScreenBatchRequest(
                candidate_path=request.candidate_path,
                baseline_export_dir=request.baseline_export_dir,
                output_dir=request.output_dir,
            )
        )
        window_start, window_end, normalization_summary = resolve_normalization_window(
            candidate=request.candidate_path,
            baseline_export_dir=request.baseline_export_dir,
            normalization_summary=request.normalization_summary_path,
            window_start=request.window_start,
            window_end=request.window_end,
        )
        rows_outside_window = count_candidate_rows_outside_window(
            request.candidate_path,
            window_start=window_start,
            window_end=window_end,
        )
        staged_path: Path | None = None
        import_ready_copy_path: Path | None = None
        staged = response.passed and rows_outside_window == 0
        blocked_reason_codes = list(response.blocked_reason_codes)
        if rows_outside_window:
            blocked_reason_codes.append("normalization_window_mismatch")
        if staged:
            staged_name = request.staged_name or request.candidate_path.name
            staged_path = request.output_dir / staged_name
            shutil.copy2(request.candidate_path, staged_path)
            if request.import_ready_dir is not None:
                request.import_ready_dir.mkdir(parents=True, exist_ok=True)
                import_ready_copy_path = request.import_ready_dir / staged_name
                shutil.copy2(request.candidate_path, import_ready_copy_path)
        self._screening.artifacts.write_json(
            request.output_dir / "stage_summary.json",
            cast(
                JsonValue,
                {
                    "status": "staged" if staged else "blocked",
                    "staged": staged,
                    "duplicate_count": response.duplicate_count,
                    "issue_count": response.issue_count,
                    "overlap_rows_flagged": response.overlap_rows_flagged,
                    "rows_outside_normalization_window": rows_outside_window,
                    "normalization_window_start": window_start,
                    "normalization_window_end": window_end,
                    "normalization_summary": normalization_summary,
                    "normalized_timezone": NORMALIZED_TIMEZONE,
                    "output_import_timezone": OUTPUT_IMPORT_TIMEZONE,
                    "staged_path": "" if staged_path is None else str(staged_path),
                    "import_ready_copy_path": "" if import_ready_copy_path is None else str(import_ready_copy_path),
                    "blocked_reason_codes": blocked_reason_codes,
                },
            ),
        )
        return StageBatchResponse(
            output_dir=request.output_dir,
            staged=staged,
            duplicate_count=response.duplicate_count,
            issue_count=response.issue_count,
            blocked_reason_codes=tuple(blocked_reason_codes),
            staged_path=staged_path,
            import_ready_copy_path=import_ready_copy_path,
            overlap_rows_flagged=response.overlap_rows_flagged,
        )
