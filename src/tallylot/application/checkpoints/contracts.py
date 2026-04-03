"""Checkpoint capability request and response contracts."""

from __future__ import annotations

from dataclasses import dataclass

from tallylot.domain.types import ResourceRef


@dataclass(frozen=True)
class LocationInventoryRequest:
    normalized_dataset_ref: ResourceRef
    inventory_output_ref: ResourceRef


@dataclass(frozen=True)
class LocationInventoryResponse:
    inventory_output_ref: ResourceRef
    location_count: int
    evidence_count: int
    issue_count: int


@dataclass(frozen=True)
class PdfBalanceExtractRequest:
    pdf_artifact_ref: ResourceRef
    output_ref: ResourceRef
    statement_kind: str | None = None


@dataclass(frozen=True)
class PdfBalanceExtractResponse:
    output_ref: ResourceRef
    row_count: int
    statement_kind: str
