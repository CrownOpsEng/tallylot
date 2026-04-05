"""Canonical materialization for validated manual balance submissions."""

from __future__ import annotations

from dataclasses import dataclass

from tallylot.adapters.support import (
    LocationRecordSpec,
    location_id_from_parts,
    location_record,
)
from tallylot.domain.checkpoints import BalanceSnapshot
from tallylot.domain.instruments import InstrumentId
from tallylot.domain.locations import LocationKind
from tallylot.domain.reconciliation import BalanceEvidence
from tallylot.domain.types import SourceId
from tallylot.ports.evidence import LocationInventoryRecord

from .contracts import (
    BalanceSubmissionRow,
    LocationInventorySubmissionRow,
    SubmittedBalanceEvidenceRow,
)
from .schema import LOCATION_INVENTORY_FILENAME, MANUAL_SUBMISSION_EVIDENCE_KIND


@dataclass(frozen=True)
class MaterializedBalanceSubmission:
    balances: tuple[BalanceSnapshot, ...]
    balance_evidence: tuple[BalanceEvidence, ...]
    location_inventory: tuple[LocationInventoryRecord, ...]


def materialize_balance_submission(
    *,
    submission_root: str,
    balance_rows: tuple[BalanceSubmissionRow, ...],
    balance_evidence_rows: tuple[SubmittedBalanceEvidenceRow, ...],
    location_inventory_rows: tuple[LocationInventorySubmissionRow, ...],
) -> MaterializedBalanceSubmission:
    return MaterializedBalanceSubmission(
        balances=tuple(_balance_snapshot_from_row(row) for row in balance_rows),
        balance_evidence=tuple(
            _balance_evidence_from_row(row) for row in balance_evidence_rows
        ),
        location_inventory=tuple(
            _location_inventory_record_from_row(row, submission_root=submission_root)
            for row in location_inventory_rows
        ),
    )


def _balance_snapshot_from_row(row: BalanceSubmissionRow) -> BalanceSnapshot:
    return BalanceSnapshot(
        source=SourceId(row.source),
        location_id=location_id_from_parts(row.source, row.account, row.wallet),
        instrument_id=InstrumentId(row.instrument_id),
        quantity=row.quantity,
        as_of_at=row.as_of_at,
        as_of_precision=row.as_of_precision,
        balance_kind=row.balance_kind,
        notes=row.notes,
    )


def _balance_evidence_from_row(row: SubmittedBalanceEvidenceRow) -> BalanceEvidence:
    return BalanceEvidence(
        source=SourceId(row.source),
        location_id=location_id_from_parts(row.source, row.account, row.wallet),
        instrument_id=InstrumentId(row.instrument_id),
        quantity=row.quantity,
        as_of_at=row.as_of_at,
        as_of_precision=row.as_of_precision,
        balance_kind=row.balance_kind,
        evidence_ref=row.evidence_ref,
        notes=row.notes,
    )


def _location_inventory_record_from_row(
    row: LocationInventorySubmissionRow,
    *,
    submission_root: str,
) -> LocationInventoryRecord:
    location_id = location_id_from_parts(row.source, row.account, row.wallet)
    account_level = row.account == row.wallet
    parent_location_id = (
        None if account_level else location_id_from_parts(row.source, row.account)
    )
    return location_record(
        LocationRecordSpec(
            source=row.source,
            location_id=location_id,
            location_kind=(
                LocationKind.ACCOUNT if account_level else LocationKind.SUBACCOUNT
            ),
            location_label=row.wallet,
            parent_location_id=parent_location_id,
            location_path=(
                (row.wallet,) if account_level else (row.account, row.wallet)
            ),
            identifier_kind=row.identifier_kind,
            identifier_value=row.identifier_value,
            network_scope=row.network_scope,
            controller=row.controller,
            evidence_kind=MANUAL_SUBMISSION_EVIDENCE_KIND,
            evidence_path=LOCATION_INVENTORY_FILENAME,
            confidence=row.confidence,
            note=row.notes,
            capture_path=submission_root,
            parent_location_label="" if account_level else row.account,
        )
    )
