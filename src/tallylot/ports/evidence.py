"""Typed evidence repository ports and records."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from tallylot.domain.checkpoints import BalanceSnapshot
from tallylot.domain.issues import IssueRecord, NormalizationReviewRecord
from tallylot.domain.locations import LocationKind
from tallylot.domain.reconciliation import BalanceEvidence
from tallylot.domain.types import LocationId
from tallylot.ports.annotations import AdapterMetadata


@dataclass(frozen=True)
class LocationInventoryRecord:
    source: str
    location_id: LocationId
    location_kind: LocationKind
    location_label: str
    identifier_kind: str
    identifier_value: str
    parent_location_id: LocationId | None = None
    location_path: tuple[str, ...] = ()
    capture_path: str = ""
    normalized_identifier: str = ""
    display_identifier: str = ""
    network_scope: str = ""
    controller: str = ""
    parent_location_label: str = ""
    evidence_kind: str = ""
    evidence_path: str = ""
    confidence: str = ""
    notes: str = ""
    adapter_metadata: tuple[AdapterMetadata, ...] = ()

    def to_row(self) -> dict[str, str]:
        return {
            "source": self.source,
            "capture_path": self.capture_path,
            "location_id": str(self.location_id),
            "location_kind": self.location_kind.value,
            "location_label": self.location_label,
            "parent_location_id": "" if self.parent_location_id is None else str(self.parent_location_id),
            "location_path": " / ".join(self.location_path),
            "identifier_kind": self.identifier_kind,
            "normalized_identifier": self.normalized_identifier or self.identifier_value,
            "display_identifier": self.display_identifier or self.identifier_value,
            "network_scope": self.network_scope,
            "controller": self.controller,
            "parent_location_label": self.parent_location_label,
            "evidence_kind": self.evidence_kind,
            "evidence_path": self.evidence_path,
            "confidence": self.confidence,
            "identifier_value": self.identifier_value,
            "notes": self.notes,
        }


class EvidenceRepositoryPort(Protocol):
    def read_balance_snapshots(self, path: Path) -> tuple[BalanceSnapshot, ...]: ...

    def write_balance_snapshots(self, path: Path, balances: tuple[BalanceSnapshot, ...]) -> None: ...

    def read_balance_evidence(self, path: Path) -> tuple[BalanceEvidence, ...]: ...

    def write_balance_evidence(self, path: Path, evidence: tuple[BalanceEvidence, ...]) -> None: ...

    def write_issue_records(self, path: Path, issues: tuple[IssueRecord, ...]) -> None: ...

    def write_review_records(self, path: Path, reviews: tuple[NormalizationReviewRecord, ...]) -> None: ...

    def write_location_inventory(self, path: Path, location_inventory: tuple[LocationInventoryRecord, ...]) -> None: ...
