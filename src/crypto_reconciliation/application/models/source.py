"""Source workflow request and response models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


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
    transaction_count: int
    balance_count: int
    issue_count: int
    review_count: int


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
class PdfBalanceExtractRequest:
    pdf_path: Path
    output_path: Path
    statement_kind: str | None = None


@dataclass(frozen=True)
class PdfBalanceExtractResponse:
    output_path: Path
    row_count: int
    statement_kind: str
