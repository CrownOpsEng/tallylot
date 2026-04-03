"""Reconciliation capability request and response contracts."""

from __future__ import annotations

from dataclasses import dataclass

from tallylot.domain.types import ResourceRef


@dataclass(frozen=True)
class BalanceAssertionRequest:
    snapshot_input_ref: ResourceRef
    evidence_input_ref: ResourceRef
    assertion_output_ref: ResourceRef


@dataclass(frozen=True)
class BalanceAssertionResponse:
    assertion_output_ref: ResourceRef
    assertion_count: int
    issue_count: int
