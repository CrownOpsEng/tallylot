"""Intake capability request and response contracts."""

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
