"""Intake capability request and response contracts."""

from __future__ import annotations

from dataclasses import dataclass

from tallylot.domain.types import ResourceRef, WorkspacePath


@dataclass(frozen=True)
class ManifestRequest:
    source_capture_ref: ResourceRef
    manifest_output_ref: ResourceRef
    inspect_archives: bool = True


@dataclass(frozen=True)
class ManifestResponse:
    manifest_output_ref: ResourceRef
    file_count: int
    manifest_fingerprint: str
    issue_count: int = 0


@dataclass(frozen=True)
class IntakePlanRequest:
    incoming_capture_ref: ResourceRef
    workspace_root_ref: WorkspacePath
    report_output_ref: ResourceRef
    inspect_archives: bool = True


@dataclass(frozen=True)
class IntakePlanResponse:
    report_output_ref: ResourceRef
    file_count: int
    issue_count: int
    planned_copy_count: int


@dataclass(frozen=True)
class IntakeApplyRequest:
    incoming_capture_ref: ResourceRef
    workspace_root_ref: WorkspacePath
    report_output_ref: ResourceRef
    inspect_archives: bool = True


@dataclass(frozen=True)
class IntakeApplyResponse:
    report_output_ref: ResourceRef
    file_count: int
    issue_count: int
    copied_count: int
