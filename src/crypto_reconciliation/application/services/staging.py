"""Batch screening and staging services."""

from __future__ import annotations

import csv
import json
import shutil
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import cast

from crypto_reconciliation.adapters.outputs.cointracking_csv import COINTRACKING_HEADER
from crypto_reconciliation.application.dtos import (
    ScreenBatchRequest,
    ScreenBatchResponse,
    StageBatchRequest,
    StageBatchResponse,
)
from crypto_reconciliation.application.services.overlap import (
    OverlapResult,
    summarize_candidate_overlap,
    write_overlap_artifacts,
)
from crypto_reconciliation.domain.models import IssueRecord
from crypto_reconciliation.domain.types import JsonValue
from crypto_reconciliation.domain.value_objects import parse_timestamp
from crypto_reconciliation.ports.artifacts import ArtifactStorePort

CANONICAL_TIMEZONE = "UTC"
COINTRACKING_IMPORT_TIMEZONE = "UTC"
DEFAULT_NORMALIZATION_WINDOW_END = "2025-12-31 23:59:59"
ISSUE_HEADER = (
    "issue_id",
    "source",
    "adapter_id",
    "severity",
    "kind",
    "message",
    "raw_file",
    "raw_row_ref",
    "status",
)


@dataclass(frozen=True)
class _ScreeningResult:
    candidate_rows: int
    issues: tuple[IssueRecord, ...]
    duplicate_count: int
    has_time_overlap: bool
    overlap_result: OverlapResult | None = None

    @property
    def passed(self) -> bool:
        overlap_flagged = False if self.overlap_result is None else bool(self.overlap_result.summary["rows_flagged"])
        return not self.issues and self.duplicate_count == 0 and not self.has_time_overlap and not overlap_flagged

    @property
    def blocked_reason_codes(self) -> tuple[str, ...]:
        reasons: list[str] = []
        if self.issues:
            reasons.append("candidate_validation_failed")
        if self.duplicate_count:
            reasons.append("duplicate_tx_id")
        if self.has_time_overlap:
            reasons.append("time_overlap")
        if self.overlap_result is not None and self.overlap_result.summary["rows_flagged"]:
            reasons.append("overlap_review_required")
        return tuple(reasons)


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

    def _screen(self, candidate_path: Path, baseline_export_dir: Path) -> _ScreeningResult:
        baseline_trade_table = _find_export(baseline_export_dir, "Trade Table")
        baseline_rows = self._artifacts.read_rows(baseline_trade_table)
        baseline_cutoff = max(parse_timestamp(row["Date"]) for row in baseline_rows if row.get("Date"))
        baseline_tx_ids = {row.get("Tx-ID", "") for row in baseline_rows if row.get("Tx-ID")}

        issues, candidate_rows, valid_rows = _candidate_validation_issues(candidate_path)
        duplicate_count = sum(1 for row in valid_rows if row["Tx-ID"] in baseline_tx_ids)
        has_time_overlap = any(parse_timestamp(row["Date"]) <= baseline_cutoff for row in valid_rows)
        overlap_result = None if issues else summarize_candidate_overlap(baseline_export_dir, candidate_path)
        return _ScreeningResult(
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
        window_start, window_end, normalization_summary = _resolve_normalization_window(
            candidate=request.candidate_path,
            baseline_export_dir=request.baseline_export_dir,
            normalization_summary=request.normalization_summary_path,
            window_start=request.window_start,
            window_end=request.window_end,
        )
        rows_outside_window = _count_candidate_rows_outside_window(
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


def _candidate_validation_issues(candidate_path: Path) -> tuple[list[IssueRecord], int, list[dict[str, str]]]:
    with candidate_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        header = tuple(reader.fieldnames or ())
        issues: list[IssueRecord] = []
        if header != COINTRACKING_HEADER:
            issues.append(
                IssueRecord(
                    issue_id=f"{candidate_path.name}:schema",
                    source="batch_screen",
                    adapter_id="cointracking_csv",
                    severity="high",
                    kind="invalid_schema",
                    message="The candidate file does not match the CoinTracking CSV header.",
                    raw_file=candidate_path.name,
                )
            )
            return issues, 0, []

        rows = list(reader)
    valid_rows: list[dict[str, str]] = []
    for index, row in enumerate(rows, start=2):
        date_value = (row.get("Date") or "").strip()
        tx_id = (row.get("Tx-ID") or "").strip()
        if not date_value:
            issues.append(_issue(candidate_path, index, "missing_date", "Candidate rows must include Date."))
            continue
        if not tx_id:
            issues.append(_issue(candidate_path, index, "missing_tx_id", "Candidate rows must include Tx-ID."))
            continue
        try:
            parse_timestamp(date_value)
        except ValueError:
            issues.append(
                _issue(
                    candidate_path,
                    index,
                    "invalid_date",
                    f"Unsupported Date value: {date_value!r}.",
                )
            )
            continue
        valid_rows.append(row)
    return issues, len(rows), valid_rows


def _issue(candidate_path: Path, row_ref: int, kind: str, message: str) -> IssueRecord:
    return IssueRecord(
        issue_id=f"{candidate_path.name}:{row_ref}:{kind}",
        source="batch_screen",
        adapter_id="cointracking_csv",
        severity="high",
        kind=kind,
        message=message,
        raw_file=candidate_path.name,
        raw_row_ref=str(row_ref),
    )


def _find_export(export_dir: Path, stem: str) -> Path:
    matches = [path for path in export_dir.glob("*.csv") if stem.lower() in path.name.lower()]
    if len(matches) != 1:
        raise FileNotFoundError(f"expected exactly one export containing {stem!r} in {export_dir}")
    return matches[0]


def _resolve_normalization_window(
    *,
    candidate: Path,
    baseline_export_dir: Path,
    normalization_summary: Path | None,
    window_start: str | None,
    window_end: str | None,
) -> tuple[str, str, str]:
    baseline_trade_table = _find_export(baseline_export_dir, "Trade Table")
    baseline_rows = _read_candidate_rows(baseline_trade_table)
    baseline_cutoff = max(parse_timestamp(row["Date"]) for row in baseline_rows if row.get("Date"))
    effective_window_start = (
        window_start
        if window_start is not None
        else (baseline_cutoff + timedelta(seconds=1)).strftime("%Y-%m-%d %H:%M:%S")
    )
    effective_window_end = DEFAULT_NORMALIZATION_WINDOW_END if window_end is None else window_end
    summary_path = normalization_summary
    if summary_path is None:
        sibling_path = candidate.parent / "normalization_summary.json"
        if sibling_path.exists():
            summary_path = sibling_path
    if summary_path is None:
        return effective_window_start, effective_window_end, ""
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Normalization summary must be a JSON object: {summary_path}")
    typed_payload = cast(dict[str, object], payload)
    if window_start is None:
        summary_start = typed_payload.get("normalization_window_start")
        if isinstance(summary_start, str) and summary_start:
            effective_window_start = summary_start
    if window_end is None:
        summary_end = typed_payload.get("normalization_window_end")
        if isinstance(summary_end, str) and summary_end:
            effective_window_end = summary_end
    return effective_window_start, effective_window_end, str(summary_path.resolve())


def _count_candidate_rows_outside_window(
    candidate_path: Path,
    *,
    window_start: str,
    window_end: str,
) -> int:
    start_dt = parse_timestamp(window_start)
    end_dt = parse_timestamp(window_end)
    rows_outside_window = 0
    for row in _read_candidate_rows(candidate_path):
        date_value = (row.get("Date") or "").strip()
        if not date_value:
            continue
        date_dt = parse_timestamp(date_value)
        if date_dt < start_dt or date_dt > end_dt:
            rows_outside_window += 1
    return rows_outside_window


def _read_candidate_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _summary_int(summary: dict[str, object], key: str) -> int:
    value = summary.get(key, 0)
    return value if isinstance(value, int) else 0
