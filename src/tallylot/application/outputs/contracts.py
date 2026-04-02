"""Output capability request and response contracts."""

from __future__ import annotations

from dataclasses import dataclass

from tallylot.domain.types import ResourceRef


@dataclass(frozen=True)
class RenderOutputRequest:
    output_adapter: str
    facts_ref: ResourceRef
    output_ref: ResourceRef


@dataclass(frozen=True)
class RenderOutputResponse:
    output_ref: ResourceRef
    row_count: int
