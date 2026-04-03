"""Dev-only oracle contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from tallylot.domain.issues import IssueRecord
from tallylot.domain.types import JsonValue


@dataclass(frozen=True)
class SourceDiffRequest:
    candidate_path: Path
    reference_path: Path
    output_dir: Path


@dataclass(frozen=True)
class SourceDiffResponse:
    output_dir: Path
    candidate_only_count: int
    reference_only_count: int
    matched_count: int


@dataclass(frozen=True)
class RoundScaffoldRequest:
    workspace_root: Path
    round_id: str
    phase: str
    source: str
    today: date | None = None


@dataclass(frozen=True)
class RoundScaffoldResponse:
    workspace_root: Path
    round_dir: Path
    round_log_path: Path
    readme_path: Path
    seeded: bool


@dataclass(frozen=True)
class VerificationCompareRequest:
    previous_dir: Path
    current_dir: Path
    output_dir: Path


@dataclass(frozen=True)
class VerificationCompareResponse:
    output_dir: Path
    changed_reports: int
    gate_suggestion: str


@dataclass(frozen=True)
class BaselineValidateRequest:
    export_dir: Path
    output_dir: Path


@dataclass(frozen=True)
class BaselineValidateResponse:
    output_dir: Path
    latest_timestamp: str
    asset_count: int


@dataclass(frozen=True)
class StageBatchRequest:
    candidate_path: Path
    baseline_export_dir: Path
    output_dir: Path
    staged_name: str | None = None
    import_ready_dir: Path | None = None
    normalization_summary_path: Path | None = None
    window_start: str | None = None
    window_end: str | None = None


@dataclass(frozen=True)
class ScreenBatchRequest:
    candidate_path: Path
    baseline_export_dir: Path
    output_dir: Path


@dataclass(frozen=True)
class ScreenBatchResponse:
    output_dir: Path
    passed: bool
    duplicate_count: int
    has_time_overlap: bool
    candidate_rows: int
    issue_count: int
    blocked_reason_codes: tuple[str, ...]
    overlap_rows_flagged: int = 0


@dataclass(frozen=True)
class StageBatchResponse:
    output_dir: Path
    staged: bool
    duplicate_count: int
    issue_count: int
    blocked_reason_codes: tuple[str, ...]
    staged_path: Path | None = None
    import_ready_copy_path: Path | None = None
    overlap_rows_flagged: int = 0


@dataclass(frozen=True)
class OverlapResult:
    summary: dict[str, JsonValue]
    flagged_rows: tuple[dict[str, str], ...]


@dataclass(frozen=True)
class ScreeningResult:
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


@dataclass(frozen=True)
class BaselineArtifacts:
    asset_snapshot_rows: list[dict[str, str]]
    reconciliation_rows: list[dict[str, str]]
    negative_balances: list[dict[str, str]]
    source_activity_rows: list[dict[str, str]]
    cad_flow_rows: list[dict[str, str]]
    cad_balance_by_exchange_rows: list[dict[str, str]]
    summary: dict[str, JsonValue]
