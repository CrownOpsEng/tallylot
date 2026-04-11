"""Filesystem-backed evidence repositories and fact persistence."""

from __future__ import annotations

from pathlib import Path

from tallylot.domain.checkpoints import BalanceSnapshot
from tallylot.domain.issues import IssueRecord, NormalizationReviewRecord
from tallylot.domain.reconciliation import BalanceConfirmation, BalanceEvidence
from tallylot.domain.transactions import TransactionFact
from tallylot.infrastructure.serialization.csv_io import write_rows
from tallylot.infrastructure.serialization.filesystem import FilesystemArtifactStore
from tallylot.ports.evidence import (
    BALANCE_CONFIRMATION_HEADER,
    BALANCE_EVIDENCE_HEADER,
    BALANCE_SNAPSHOT_HEADER,
    ISSUE_HEADER,
    LOCATION_INVENTORY_HEADER,
    NORMALIZATION_REVIEW_HEADER,
    LocationInventoryRecord,
)
from tallylot.ports.facts import FACT_HEADER

from .balance_codec import (
    balance_confirmation_from_row,
    balance_evidence_from_row,
    balance_snapshot_from_row,
)
from .fact_codec import fact_from_row


class FilesystemFactRepository:
    def __init__(self) -> None:
        self._artifacts = FilesystemArtifactStore()

    def read_facts(self, path: Path) -> tuple[TransactionFact, ...]:
        rows = self._artifacts.read_rows(path)
        return tuple(fact_from_row(row) for row in rows)

    def write_facts(self, path: Path, facts: tuple[TransactionFact, ...]) -> None:
        write_rows(path, FACT_HEADER, (fact.to_row() for fact in facts))


class FilesystemEvidenceRepository:
    def __init__(self) -> None:
        self._artifacts = FilesystemArtifactStore()

    def read_balance_snapshots(
        self,
        path: Path,
    ) -> tuple[BalanceSnapshot, ...]:
        rows = self._artifacts.read_rows(path)
        return tuple(balance_snapshot_from_row(row) for row in rows)

    def write_balance_snapshots(
        self, path: Path, balances: tuple[BalanceSnapshot, ...]
    ) -> None:
        write_rows(
            path,
            BALANCE_SNAPSHOT_HEADER,
            (balance.to_row() for balance in balances),
        )

    def read_balance_evidence(
        self,
        path: Path,
    ) -> tuple[BalanceEvidence, ...]:
        rows = self._artifacts.read_rows(path)
        return tuple(balance_evidence_from_row(row) for row in rows)

    def write_balance_evidence(
        self, path: Path, evidence: tuple[BalanceEvidence, ...]
    ) -> None:
        write_rows(
            path,
            BALANCE_EVIDENCE_HEADER,
            (record.to_row() for record in evidence),
        )

    def read_balance_confirmations(
        self,
        path: Path,
    ) -> tuple[BalanceConfirmation, ...]:
        rows = self._artifacts.read_rows(path)
        return tuple(balance_confirmation_from_row(row) for row in rows)

    def write_balance_confirmations(
        self,
        path: Path,
        confirmations: tuple[BalanceConfirmation, ...],
    ) -> None:
        write_rows(
            path,
            BALANCE_CONFIRMATION_HEADER,
            (record.to_row() for record in confirmations),
        )

    def write_issue_records(self, path: Path, issues: tuple[IssueRecord, ...]) -> None:
        write_rows(
            path,
            ISSUE_HEADER,
            (issue.to_row() for issue in issues),
        )

    def write_review_records(
        self,
        path: Path,
        reviews: tuple[NormalizationReviewRecord, ...],
    ) -> None:
        write_rows(
            path,
            NORMALIZATION_REVIEW_HEADER,
            (review.to_row() for review in reviews),
        )

    def write_location_inventory(
        self, path: Path, location_inventory: tuple[LocationInventoryRecord, ...]
    ) -> None:
        write_rows(
            path,
            LOCATION_INVENTORY_HEADER,
            (record.to_row() for record in location_inventory),
        )
