"""Application request and response models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WorkspaceInitRequest:
    workspace_root: Path


@dataclass(frozen=True)
class WorkspaceInitResponse:
    workspace_root: Path
    created_paths: tuple[Path, ...]


@dataclass(frozen=True)
class ManifestRequest:
    source_dir: Path
    output_path: Path
    inspect_archives: bool = True


@dataclass(frozen=True)
class ManifestResponse:
    output_path: Path
    file_count: int
    manifest_fingerprint: str
    issue_count: int = 0


@dataclass(frozen=True)
class ProfileRequest:
    source: str
    raw_dir: Path
    output_dir: Path
    inspect_archives: bool = True


@dataclass(frozen=True)
class ProfileResponse:
    output_dir: Path
    adapter_id: str
    file_count: int
    supported: bool
    issue_count: int = 0


@dataclass(frozen=True)
class IntakePlanRequest:
    incoming_dir: Path
    workspace_root: Path
    report_dir: Path
    inspect_archives: bool = True


@dataclass(frozen=True)
class IntakePlanResponse:
    report_dir: Path
    file_count: int
    issue_count: int
    planned_copy_count: int


@dataclass(frozen=True)
class IntakeApplyRequest:
    incoming_dir: Path
    workspace_root: Path
    report_dir: Path
    inspect_archives: bool = True


@dataclass(frozen=True)
class IntakeApplyResponse:
    report_dir: Path
    file_count: int
    issue_count: int
    copied_count: int


@dataclass(frozen=True)
class NormalizeRequest:
    source: str
    raw_dir: Path
    output_dir: Path
    window_start: str | None = None
    window_end: str | None = None
    inspect_archives: bool = True


@dataclass(frozen=True)
class NormalizeResponse:
    output_dir: Path
    adapter_id: str
    event_count: int
    balance_count: int
    issue_count: int
    review_count: int


@dataclass(frozen=True)
class WalletInventoryRequest:
    normalized_root: Path
    output_path: Path


@dataclass(frozen=True)
class WalletInventoryResponse:
    output_path: Path
    wallet_count: int
    evidence_count: int
    issue_count: int


@dataclass(frozen=True)
class RenderCoinTrackingRequest:
    canonical_events_path: Path
    output_path: Path


@dataclass(frozen=True)
class RenderCoinTrackingResponse:
    output_path: Path
    row_count: int


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
class RoundScaffoldRequest:
    workspace_root: Path
    round_id: str
    phase: str
    source: str


@dataclass(frozen=True)
class RoundScaffoldResponse:
    workspace_root: Path
    round_dir: Path
    round_log_path: Path
    seeded: bool


@dataclass(frozen=True)
class SourceReconcileRequest:
    candidate_path: Path
    reference_path: Path
    output_dir: Path


@dataclass(frozen=True)
class SourceReconcileResponse:
    output_dir: Path
    candidate_only_count: int
    reference_only_count: int
    matched_count: int


@dataclass(frozen=True)
class PdfBalanceExtractRequest:
    pdf_path: Path
    output_path: Path
    statement_kind: str | None = None


@dataclass(frozen=True)
class PdfBalanceExtractResponse:
    output_path: Path
    row_count: int
    statement_kind: str
