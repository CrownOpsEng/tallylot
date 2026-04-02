"""Batch screening and staging services."""

from __future__ import annotations

import csv
import shutil
from dataclasses import dataclass
from pathlib import Path

from crypto_reconciliation.adapters.outputs.cointracking_csv import COINTRACKING_HEADER
from crypto_reconciliation.application.dtos import (
    ScreenBatchRequest,
    ScreenBatchResponse,
    StageBatchRequest,
    StageBatchResponse,
)
from crypto_reconciliation.domain.models import IssueRecord
from crypto_reconciliation.domain.value_objects import parse_timestamp
from crypto_reconciliation.ports.artifacts import ArtifactStorePort

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

    @property
    def passed(self) -> bool:
        return not self.issues and self.duplicate_count == 0 and not self.has_time_overlap

    @property
    def blocked_reason_codes(self) -> tuple[str, ...]:
        reasons: list[str] = []
        if self.issues:
            reasons.append("candidate_validation_failed")
        if self.duplicate_count:
            reasons.append("duplicate_tx_id")
        if self.has_time_overlap:
            reasons.append("time_overlap")
        return tuple(reasons)


class BatchScreeningService:
    def __init__(self, artifacts: ArtifactStorePort) -> None:
        self._artifacts = artifacts

    def execute(self, request: ScreenBatchRequest) -> ScreenBatchResponse:
        request.output_dir.mkdir(parents=True, exist_ok=True)
        screening = self._screen(request.candidate_path, request.baseline_export_dir)
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
        )

    def _screen(self, candidate_path: Path, baseline_export_dir: Path) -> _ScreeningResult:
        baseline_trade_table = _find_export(baseline_export_dir, "Trade Table")
        baseline_rows = self._artifacts.read_rows(baseline_trade_table)
        baseline_cutoff = max(parse_timestamp(row["Date"]) for row in baseline_rows if row.get("Date"))
        baseline_tx_ids = {row.get("Tx-ID", "") for row in baseline_rows if row.get("Tx-ID")}

        issues, candidate_rows, valid_rows = _candidate_validation_issues(candidate_path)
        duplicate_count = sum(1 for row in valid_rows if row["Tx-ID"] in baseline_tx_ids)
        has_time_overlap = any(parse_timestamp(row["Date"]) <= baseline_cutoff for row in valid_rows)
        return _ScreeningResult(
            candidate_rows=candidate_rows,
            issues=tuple(issues),
            duplicate_count=duplicate_count,
            has_time_overlap=has_time_overlap,
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
        if response.passed:
            shutil.copy2(request.candidate_path, request.output_dir / request.candidate_path.name)
        return StageBatchResponse(
            output_dir=request.output_dir,
            staged=response.passed,
            duplicate_count=response.duplicate_count,
            issue_count=response.issue_count,
            blocked_reason_codes=response.blocked_reason_codes,
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
