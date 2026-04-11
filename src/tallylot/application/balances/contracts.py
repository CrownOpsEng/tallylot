"""Balance capability request and response contracts."""

from __future__ import annotations

from dataclasses import dataclass

from tallylot.application.balances.records import BalanceResolutionMode
from tallylot.domain.types import ResourceRef


@dataclass(frozen=True)
class BalanceInspectRequest:
    input_root_ref: ResourceRef
    inspect_output_ref: ResourceRef


@dataclass(frozen=True)
class BalanceInspectResponse:
    inspect_output_ref: ResourceRef
    inspect_summary_output_ref: ResourceRef
    source_count: int
    comparable_source_count: int


@dataclass(frozen=True)
class BalanceCheckRequest:
    input_root_ref: ResourceRef
    output_root_ref: ResourceRef
    sources: tuple[str, ...] = ()
    as_of_values: tuple[str, ...] = ()
    hydrate_missing_references: bool = False
    reference_policy: str = "default"


@dataclass(frozen=True)
class BalanceCheckResponse:
    output_root_ref: ResourceRef
    check_summary_output_ref: ResourceRef
    source_count: int
    clean_source_count: int
    issue_source_count: int
    failed_source_count: int
    no_balance_target_source_count: int
    not_runnable_source_count: int
    resolution_mode: BalanceResolutionMode


@dataclass(frozen=True)
class BalanceSummaryRequest:
    inspect_input_ref: ResourceRef
    check_summary_input_ref: ResourceRef
    summary_output_ref: ResourceRef


@dataclass(frozen=True)
class BalanceSummaryResponse:
    summary_output_ref: ResourceRef
    blocker_output_ref: ResourceRef
    source_count: int
    latest_portfolio_clean_date: str
    latest_portfolio_resolved_reference_date: str
    latest_clean_source_date: str
    latest_resolved_reference_date: str
    latest_observed_assertion_date: str
