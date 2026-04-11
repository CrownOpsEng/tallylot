"""Typed evidence repository ports and records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Protocol

from tallylot.domain.captures import ProvenanceLocator, provenance_locator_header
from tallylot.domain.checkpoints import BalanceSnapshot
from tallylot.domain.issues import IssueRecord, NormalizationReviewRecord
from tallylot.domain.locations import LocationKind
from tallylot.domain.reconciliation import BalanceConfirmation, BalanceEvidence
from tallylot.domain.temporal import TemporalPrecision
from tallylot.domain.types import LocationId
from tallylot.ports.annotations import AdapterMetadata

RAW_PROVENANCE_HEADER = provenance_locator_header("raw")
EVIDENCE_PROVENANCE_HEADER = provenance_locator_header("evidence")

BALANCE_SNAPSHOT_HEADER = (
    "source",
    "location_id",
    "instrument_id",
    "quantity",
    "as_of_at",
    "as_of_precision",
    "balance_kind",
    "notes",
)
BALANCE_EVIDENCE_HEADER = (
    "source",
    "location_id",
    "instrument_id",
    "quantity",
    "as_of_at",
    "as_of_precision",
    "balance_kind",
    *provenance_locator_header(),
    "notes",
)
BALANCE_CONFIRMATION_HEADER = (
    "source",
    "location_id",
    "instrument_id",
    "quantity",
    "as_of_at",
    "as_of_precision",
    "balance_kind",
    "confirmation_kind",
    "support_ref",
    "asserted_meaning",
    "reviewed_by",
    "reviewed_at",
    "reason",
    "notes",
)
LOCATION_INVENTORY_HEADER = (
    "source",
    "capture_uid",
    "capture_label",
    "capture_root_ref",
    "location_id",
    "location_kind",
    "location_label",
    "parent_location_id",
    "location_path",
    "identifier_kind",
    "normalized_identifier",
    "display_identifier",
    "network_scope",
    "controller",
    "parent_location_label",
    "evidence_kind",
    *EVIDENCE_PROVENANCE_HEADER,
    "confidence",
    "identifier_value",
    "notes",
)
ISSUE_HEADER = (
    "issue_id",
    "source",
    "adapter_id",
    "severity",
    "kind",
    "message",
    "context_timestamp",
    "raw_file",
    "raw_row_ref",
    *RAW_PROVENANCE_HEADER,
    "status",
)
NORMALIZATION_REVIEW_HEADER = (
    "review_id",
    "source",
    "adapter_id",
    "scope",
    "kind",
    "message",
    "context_timestamp",
    "raw_file",
    "raw_row_ref",
    *RAW_PROVENANCE_HEADER,
    "field_name",
    "original_value",
    "normalized_value",
    "status",
)


@dataclass(frozen=True)
class LocationInventoryRecord:
    source: str
    location_id: LocationId
    location_kind: LocationKind
    location_label: str
    identifier_kind: str
    identifier_value: str
    evidence_provenance: ProvenanceLocator
    parent_location_id: LocationId | None = None
    location_path: tuple[str, ...] = ()
    capture_uid: str = ""
    capture_label: str = ""
    capture_root_ref: str = ""
    normalized_identifier: str = ""
    display_identifier: str = ""
    network_scope: str = ""
    controller: str = ""
    parent_location_label: str = ""
    evidence_kind: str = ""
    confidence: str = ""
    notes: str = ""
    adapter_metadata: tuple[AdapterMetadata, ...] = ()

    def to_row(self) -> dict[str, str]:
        return {
            "source": self.source,
            "capture_uid": self.capture_uid,
            "capture_label": self.capture_label,
            "capture_root_ref": self.capture_root_ref,
            "location_id": str(self.location_id),
            "location_kind": self.location_kind.value,
            "location_label": self.location_label,
            "parent_location_id": ""
            if self.parent_location_id is None
            else str(self.parent_location_id),
            "location_path": " / ".join(self.location_path),
            "identifier_kind": self.identifier_kind,
            "normalized_identifier": self.normalized_identifier
            or self.identifier_value,
            "display_identifier": self.display_identifier or self.identifier_value,
            "network_scope": self.network_scope,
            "controller": self.controller,
            "parent_location_label": self.parent_location_label,
            "evidence_kind": self.evidence_kind,
            **self.evidence_provenance.to_flat_dict(prefix="evidence"),
            "confidence": self.confidence,
            "identifier_value": self.identifier_value,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class StatementDocumentBalanceRow:
    source: str
    account: str
    wallet: str
    balance_kind: str
    asset: str
    quantity: Decimal | None
    as_of_at: datetime | None
    as_of_precision: TemporalPrecision
    pdf_file: str
    as_of_text: str = ""
    raw_row_ref: str = ""
    notes: str = ""
    staked_quantity: str = ""
    value_amount: str = ""
    value_currency: str = ""
    price_amount: str = ""
    price_currency: str = ""


@dataclass(frozen=True)
class StatementDocumentParseResult:
    pdf_file: str
    recognized: bool
    statement_as_of_at: datetime | None
    rows: tuple[StatementDocumentBalanceRow, ...]
    document_effective_at: datetime | None = None


@dataclass(frozen=True)
class StatementBalanceEvidenceBatch:
    balance_evidence: tuple[BalanceEvidence, ...]
    issues: tuple[IssueRecord, ...]
    reviews: tuple[NormalizationReviewRecord, ...]


class EvidenceRepositoryPort(Protocol):
    def read_balance_snapshots(self, path: Path) -> tuple[BalanceSnapshot, ...]: ...

    def write_balance_snapshots(
        self, path: Path, balances: tuple[BalanceSnapshot, ...]
    ) -> None: ...

    def read_balance_evidence(self, path: Path) -> tuple[BalanceEvidence, ...]: ...

    def write_balance_evidence(
        self, path: Path, evidence: tuple[BalanceEvidence, ...]
    ) -> None: ...

    def read_balance_confirmations(
        self, path: Path
    ) -> tuple[BalanceConfirmation, ...]: ...

    def write_balance_confirmations(
        self, path: Path, confirmations: tuple[BalanceConfirmation, ...]
    ) -> None: ...

    def write_issue_records(
        self, path: Path, issues: tuple[IssueRecord, ...]
    ) -> None: ...

    def write_review_records(
        self, path: Path, reviews: tuple[NormalizationReviewRecord, ...]
    ) -> None: ...

    def write_location_inventory(
        self, path: Path, location_inventory: tuple[LocationInventoryRecord, ...]
    ) -> None: ...
