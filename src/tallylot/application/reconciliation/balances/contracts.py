"""Balance reconciliation request and response contracts."""

from __future__ import annotations

from dataclasses import dataclass

from tallylot.domain.types import ResourceRef


@dataclass(frozen=True)
class BalanceCoverageRequest:
    input_root_ref: ResourceRef
    coverage_output_ref: ResourceRef


@dataclass(frozen=True)
class BalanceCoverageResponse:
    coverage_output_ref: ResourceRef
    coverage_summary_output_ref: ResourceRef
    source_count: int
    comparable_source_count: int


@dataclass(frozen=True)
class BalanceCheckRequest:
    input_root_ref: ResourceRef
    output_root_ref: ResourceRef
    sources: tuple[str, ...] = ()


@dataclass(frozen=True)
class BalanceCheckResponse:
    output_root_ref: ResourceRef
    check_summary_output_ref: ResourceRef
    source_count: int
    clean_source_count: int
    issue_source_count: int
    failed_source_count: int
    no_assertion_source_count: int


@dataclass(frozen=True)
class BalanceSummaryRequest:
    coverage_input_ref: ResourceRef
    check_summary_input_ref: ResourceRef
    summary_output_ref: ResourceRef


@dataclass(frozen=True)
class BalanceSummaryResponse:
    summary_output_ref: ResourceRef
    blocker_output_ref: ResourceRef
    source_count: int
    latest_portfolio_clean_date: str
    latest_portfolio_source_backed_date: str
    latest_clean_source_date: str
    latest_source_backed_date: str
    latest_observed_assertion_date: str
