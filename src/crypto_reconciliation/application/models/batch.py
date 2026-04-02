"""Batch workflow request and response models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


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
