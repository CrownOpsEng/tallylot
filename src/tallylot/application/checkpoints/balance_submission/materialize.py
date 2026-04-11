"""Canonical materialization for validated manual balance submissions."""

from __future__ import annotations

from dataclasses import dataclass

from tallylot.adapters.support import (
    LocationRecordSpec,
    location_id_from_parts,
    location_record,
)
from tallylot.domain.captures import ProvenanceLocator
from tallylot.domain.balances import (
    BalanceReference,
    BalanceReferenceKind,
    BalanceSnapshot,
    BalanceTarget,
)
from tallylot.domain.instruments import InstrumentId
from tallylot.domain.locations import LocationKind
from tallylot.domain.types import SourceId
from tallylot.ports.evidence import LocationInventoryRecord

from .contracts import (
    BalanceReferenceSubmissionRow,
    BalanceSnapshotSubmissionRow,
    LocationInventorySubmissionRow,
)
from .schema import LOCATION_INVENTORY_FILENAME, MANUAL_SUBMISSION_EVIDENCE_KIND


@dataclass(frozen=True)
class MaterializedBalanceSubmission:
    balance_snapshots: tuple[BalanceSnapshot, ...]
    balance_references: tuple[BalanceReference, ...]
    location_inventory: tuple[LocationInventoryRecord, ...]


def materialize_balance_submission(
    *,
    submission_root: str,
    balance_snapshot_rows: tuple[BalanceSnapshotSubmissionRow, ...],
    balance_reference_rows: tuple[BalanceReferenceSubmissionRow, ...],
    location_inventory_rows: tuple[LocationInventorySubmissionRow, ...],
) -> MaterializedBalanceSubmission:
    return MaterializedBalanceSubmission(
        balance_snapshots=tuple(
            _balance_snapshot_from_row(row) for row in balance_snapshot_rows
        ),
        balance_references=tuple(
            _balance_reference_from_row(row) for row in balance_reference_rows
        ),
        location_inventory=tuple(
            _location_inventory_record_from_row(row, submission_root=submission_root)
            for row in location_inventory_rows
        ),
    )


def _balance_snapshot_from_row(row: BalanceSnapshotSubmissionRow) -> BalanceSnapshot:
    return BalanceSnapshot(
        target=BalanceTarget(
            source=SourceId(row.source),
            location_id=location_id_from_parts(row.source, row.account, row.wallet),
            instrument_id=InstrumentId(row.instrument_id),
            balance_kind=row.balance_kind,
            target_at=row.target_at,
            target_precision=row.target_precision,
        ),
        quantity=row.quantity,
        snapshot_basis=MANUAL_SUBMISSION_EVIDENCE_KIND,
        notes=row.notes,
    )


def _balance_reference_from_row(
    row: BalanceReferenceSubmissionRow,
) -> BalanceReference:
    return BalanceReference(
        target=BalanceTarget(
            source=SourceId(row.source),
            location_id=location_id_from_parts(row.source, row.account, row.wallet),
            instrument_id=InstrumentId(row.instrument_id),
            balance_kind=row.balance_kind,
            target_at=row.target_at,
            target_precision=row.target_precision,
        ),
        quantity=row.quantity,
        reference_kind=BalanceReferenceKind(row.reference_kind),
        observed_at=row.observed_at,
        observed_precision=row.observed_precision,
        support_ref=row.support_ref,
        reviewed_by=row.reviewed_by,
        reviewed_at=row.reviewed_at,
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
            evidence_provenance=ProvenanceLocator.from_reference_ref(
                LOCATION_INVENTORY_FILENAME
            ),
            confidence=row.confidence,
            note=row.notes,
            capture_root_ref=str(submission_root),
            parent_location_label="" if account_level else row.account,
        )
    )
