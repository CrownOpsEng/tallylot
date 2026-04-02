"""Batch screening and staging workflows."""

from __future__ import annotations

import shutil
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import cast

from crypto_reconciliation.application.dtos import (
    ScreenBatchRequest,
    ScreenBatchResponse,
    StageBatchRequest,
    StageBatchResponse,
)
from crypto_reconciliation.domain.models import AdapterCapability
from crypto_reconciliation.domain.types import JsonValue
from crypto_reconciliation.ports.adapters import OutputAdapter, OutputAdapterRegistryPort
from crypto_reconciliation.ports.artifacts import ArtifactStorePort
from crypto_reconciliation.ports.output_workflows import OverlapResult, ScreeningResult

from .windows import count_candidate_rows_outside_window, resolve_normalization_window

CANONICAL_TIMEZONE = "UTC"
OUTPUT_IMPORT_TIMEZONE = "UTC"
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
    def __init__(self, registry: OutputAdapterRegistryPort, artifacts: ArtifactStorePort) -> None:
        self._registry = registry
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
                0
                if screening.overlap_result is None
                else _summary_int(screening.overlap_result.summary, "rows_flagged")
            ),
        )

    def _screen(self, candidate_path: Path, baseline_export_dir: Path) -> ScreeningResult:
        adapter = _resolve_review_adapter(self._registry, candidate_path, self._artifacts)
        return adapter.screen_candidate(candidate_path, baseline_export_dir, self._artifacts)


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


def _summary_int(summary: Mapping[str, JsonValue], key: str) -> int:
    value = summary.get(key, 0)
    return value if isinstance(value, int) else 0


def write_overlap_artifacts(
    output_dir: Path,
    result: OverlapResult,
    *,
    write_json: Callable[[Path, JsonValue], None],
    write_rows: Callable[[Path, tuple[str, ...], Iterable[dict[str, str]]], None],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "overlap_summary.json", result.summary)
    write_rows(output_dir / "overlap_flagged_rows.csv", OVERLAP_FLAGGED_HEADER, result.flagged_rows)


def _resolve_review_adapter(
    registry: OutputAdapterRegistryPort,
    candidate_path: Path,
    artifacts: ArtifactStorePort,
) -> OutputAdapter:
    matches = [
        (adapter.match_candidate(candidate_path, artifacts), adapter)
        for adapter in registry.output_adapters
        if adapter.manifest.supported and AdapterCapability.REVIEW in adapter.manifest.capabilities
    ]
    scored_matches = [(score, adapter) for score, adapter in matches if score > 0]
    if not scored_matches:
        raise ValueError(f"unable to detect supported output adapter for candidate {candidate_path}")
    scored_matches.sort(key=lambda item: item[0], reverse=True)
    best_score = scored_matches[0][0]
    best_adapters = [adapter for score, adapter in scored_matches if score == best_score]
    if len(best_adapters) > 1:
        adapter_ids = ", ".join(sorted(str(adapter.manifest.adapter_id) for adapter in best_adapters))
        raise ValueError(f"ambiguous output adapter for candidate {candidate_path}: {adapter_ids}")
    return best_adapters[0]


OVERLAP_FLAGGED_HEADER = (
    "row_number",
    "reasons",
    "type",
    "buy",
    "buy_currency",
    "sell",
    "sell_currency",
    "fee",
    "fee_currency",
    "exchange",
    "date",
    "tx_id",
)
