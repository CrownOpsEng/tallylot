"""Normalization capability request and response contracts."""

from __future__ import annotations

from dataclasses import dataclass

from tallylot.domain.types import ResourceRef


@dataclass(frozen=True)
class NormalizeRequest:
    source: str
    raw_capture_ref: ResourceRef
    normalized_output_ref: ResourceRef
    window_start: str | None = None
    window_end: str | None = None
    inspect_archives: bool = True


@dataclass(frozen=True)
class NormalizeResponse:
    normalized_output_ref: ResourceRef
    adapter_id: str
    fact_count: int
    balance_count: int
    issue_count: int
    review_count: int
