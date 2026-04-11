"""Shared balance artifact package seam."""

from __future__ import annotations

from dataclasses import dataclass

from tallylot.domain.balances import BalanceReference, BalanceSnapshot
from tallylot.domain.issues import IssueRecord
from tallylot.ports.evidence import LocationInventoryRecord


@dataclass(frozen=True)
class BalanceArtifactPackage:
    snapshots: tuple[BalanceSnapshot, ...]
    references: tuple[BalanceReference, ...]
    reference_issues: tuple[IssueRecord, ...]
    location_inventory: tuple[LocationInventoryRecord, ...]
