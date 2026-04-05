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


@dataclass(frozen=True)
class ScaffoldBalanceSubmissionRequest:
    source: str
    submission_root_ref: ResourceRef


@dataclass(frozen=True)
class ScaffoldBalanceSubmissionResponse:
    source: str
    submission_root_ref: ResourceRef
    readme_ref: ResourceRef
    balances_example_ref: ResourceRef
    balance_confirmations_example_ref: ResourceRef
    location_inventory_example_ref: ResourceRef


@dataclass(frozen=True)
class SubmitBalancesRequest:
    source: str
    submission_root_ref: ResourceRef
    output_root_ref: ResourceRef


@dataclass(frozen=True)
class SubmitBalancesResponse:
    submission_root_ref: ResourceRef
    output_root_ref: ResourceRef
    balance_row_count: int
    balance_confirmation_row_count: int
    location_inventory_row_count: int
    issue_count: int
    blocked: bool
    wrote_balance_confirmations: bool
    wrote_location_inventory: bool
    ready_for_balance_check: bool
    ready_for_source_backed_checkpoint: bool
    trust_tier: str
