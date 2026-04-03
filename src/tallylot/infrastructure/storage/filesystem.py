"""Filesystem-backed evidence repositories and fact persistence."""

from __future__ import annotations

from pathlib import Path

from tallylot.domain.checkpoints import BalanceSnapshot
from tallylot.domain.issues import IssueRecord, NormalizationReviewRecord
from tallylot.domain.reconciliation import BalanceEvidence
from tallylot.domain.transactions import TransactionFact
from tallylot.infrastructure.serialization.csv_io import write_rows
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tallylot.ports.evidence import LocationInventoryRecord

from .fact_codec import FACT_HEADER, fact_from_row

LOCATION_INVENTORY_HEADER = (
    "source",
    "capture_path",
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
    "evidence_path",
    "confidence",
    "identifier_value",
    "notes",
)


class FilesystemFactRepository:
    def __init__(self) -> None:
        self._artifacts = FilesystemArtifactStore()

    def read_facts(self, path: Path) -> tuple[TransactionFact, ...]:
        rows = self._artifacts.read_rows(path)
        return tuple(fact_from_row(row) for row in rows)

    def write_facts(self, path: Path, facts: tuple[TransactionFact, ...]) -> None:
        write_rows(path, FACT_HEADER, (fact.to_row() for fact in facts))


class FilesystemEvidenceRepository:
    def write_balance_snapshots(self, path: Path, balances: tuple[BalanceSnapshot, ...]) -> None:
        write_rows(
            path,
            (
                "source",
                "location_id",
                "instrument_id",
                "quantity",
                "as_of_at",
                "as_of_precision",
                "balance_kind",
                "notes",
            ),
            (balance.to_row() for balance in balances),
        )

    def write_balance_evidence(self, path: Path, evidence: tuple[BalanceEvidence, ...]) -> None:
        write_rows(
            path,
            (
                "source",
                "location_id",
                "instrument_id",
                "quantity",
                "as_of_at",
                "as_of_precision",
                "balance_kind",
                "evidence_ref",
                "notes",
            ),
            (record.to_row() for record in evidence),
        )

    def write_issue_records(self, path: Path, issues: tuple[IssueRecord, ...]) -> None:
        write_rows(
            path,
            (
                "issue_id",
                "source",
                "adapter_id",
                "severity",
                "kind",
                "message",
                "context_timestamp",
                "raw_file",
                "raw_row_ref",
                "status",
            ),
            (issue.to_row() for issue in issues),
        )

    def write_review_records(
        self,
        path: Path,
        reviews: tuple[NormalizationReviewRecord, ...],
    ) -> None:
        write_rows(
            path,
            (
                "review_id",
                "source",
                "adapter_id",
                "scope",
                "kind",
                "message",
                "context_timestamp",
                "raw_file",
                "raw_row_ref",
                "field_name",
                "original_value",
                "normalized_value",
                "status",
            ),
            (review.to_row() for review in reviews),
        )

    def write_location_inventory(self, path: Path, location_inventory: tuple[LocationInventoryRecord, ...]) -> None:
        write_rows(path, LOCATION_INVENTORY_HEADER, (record.to_row() for record in location_inventory))
