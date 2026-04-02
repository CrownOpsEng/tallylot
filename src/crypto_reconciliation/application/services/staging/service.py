"""Batch screening and staging workflows."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import cast

from crypto_reconciliation.application.dtos import (
    ScreenBatchRequest,
    ScreenBatchResponse,
    StageBatchRequest,
    StageBatchResponse,
)
from crypto_reconciliation.application.services.export_files import find_required_csv_export
from crypto_reconciliation.application.services.overlap import summarize_candidate_overlap, write_overlap_artifacts
from crypto_reconciliation.domain.types import JsonValue
from crypto_reconciliation.domain.value_objects import parse_timestamp
from crypto_reconciliation.ports.artifacts import ArtifactStorePort

from .models import ScreeningResult
from .validation import candidate_validation_issues
from .windows import count_candidate_rows_outside_window, resolve_normalization_window

CANONICAL_TIMEZONE = "UTC"
COINTRACKING_IMPORT_TIMEZONE = "UTC"
ISSUE_HEADER = (
    "issue_id",
    "source",
    "adapter_id",
    "severity",
    "kind",
    "message",
    "context_timestamp",
    "raw_file",
    "raw_row_ref",
    "status",
)


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
                    else _summary_int(screening.overlap_result.summary, "rows_flagged")
                ),
                "canonical_timezone": CANONICAL_TIMEZONE,
                "cointracking_import_timezone": COINTRACKING_IMPORT_TIMEZONE,
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
                0
                if screening.overlap_result is None
                else _summary_int(screening.overlap_result.summary, "rows_flagged")
            ),
        )

    def _screen(self, candidate_path: Path, baseline_export_dir: Path) -> ScreeningResult:
        baseline_trade_table = find_required_csv_export(baseline_export_dir, "Trade Table")
        baseline_rows = self._artifacts.read_rows(baseline_trade_table)
        baseline_cutoff = max(parse_timestamp(row["Date"]) for row in baseline_rows if row.get("Date"))
        baseline_tx_ids = {row.get("Tx-ID", "") for row in baseline_rows if row.get("Tx-ID")}

        issues, candidate_rows, valid_rows = candidate_validation_issues(candidate_path)
        duplicate_count = sum(1 for row in valid_rows if row["Tx-ID"] in baseline_tx_ids)
        has_time_overlap = any(parse_timestamp(row["Date"]) <= baseline_cutoff for row in valid_rows)
        overlap_result = None if issues else summarize_candidate_overlap(baseline_export_dir, candidate_path)
        return ScreeningResult(
            candidate_rows=candidate_rows,
            issues=tuple(issues),
            duplicate_count=duplicate_count,
            has_time_overlap=has_time_overlap,
            overlap_result=overlap_result,
        )


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
                    "canonical_timezone": CANONICAL_TIMEZONE,
                    "cointracking_import_timezone": COINTRACKING_IMPORT_TIMEZONE,
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


def _summary_int(summary: dict[str, object], key: str) -> int:
    value = summary.get(key, 0)
    return value if isinstance(value, int) else 0
