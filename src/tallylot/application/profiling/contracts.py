"""Profiling capability request and response contracts."""

from __future__ import annotations

from dataclasses import dataclass

from tallylot.domain.types import ResourceRef


@dataclass(frozen=True)
class ProfileRequest:
    source: str
    raw_capture_ref: ResourceRef
    profile_output_ref: ResourceRef
    inspect_archives: bool = True


@dataclass(frozen=True)
class ProfileResponse:
    profile_output_ref: ResourceRef
    adapter_id: str
    file_count: int
    supported: bool
    issue_count: int = 0
