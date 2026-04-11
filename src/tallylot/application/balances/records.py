"""Balance reconciliation artifact records."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal, cast

from tallylot.application.balances.inputs import (
    BalanceInputMode,
    BalanceSnapshotOrigin,
)

BALANCE_ASSERTION_HEADER = (
    "source",
    "location_id",
    "instrument_id",
    "balance_kind",
    "target_at",
    "target_precision",
    "snapshot_quantity",
    "reference_quantity",
    "difference",
    "status",
    "selected_reference_kind",
    "snapshot_basis",
    "observed_at",
    "observed_precision",
    "observation_gap",
    "support_ref",
    "provider_family",
    "provider_block_ref",
    "notes",
)

BalanceOfflineReadyStatus = Literal[
    "ready",
    "missing_references",
    "no_balance_targets",
    "no_balance_inputs",
]
BalanceCrossSourceReadyStatus = Literal[
    "ready",
    "missing_location_inventory",
    "not_comparable",
    "not_applicable",
]
BalanceCheckStatus = Literal[
    "clean",
    "issues",
    "failed",
    "no_balance_targets",
    "not_runnable",
]
BalanceResolutionMode = Literal["offline", "hydrated"]

BALANCE_INSPECT_HEADER = (
    "source",
    "input_mode",
    "snapshot_origin",
    "target_count",
    "snapshot_count",
    "reference_row_count",
    "matched_reference_count",
    "missing_reference_count",
    "source_document_count",
    "network_api_count",
    "operator_assertion_count",
    "cross_source_ready",
    "offline_ready",
    "unexpected_superseded_output_count",
    "min_target_date",
    "max_target_date",
    "min_reference_date",
    "max_reference_date",
)

BALANCE_CHECK_SUMMARY_HEADER = (
    "source",
    "resolution_mode",
    "check_status",
    "not_runnable_reason",
    "assertion_count",
    "issue_count",
    "min_assertion_date",
    "max_assertion_date",
    "latest_clean_checked_date",
    "latest_resolved_reference_checked_date",
    "assertion_status_counts",
    "selected_reference_kind_counts",
    "issue_kind_counts",
    "error_message",
)

BALANCE_RECONCILIATION_BLOCKER_HEADER = (
    "source",
    "blocker_kind",
    "blocker_count",
    "notes",
)

CROSS_SOURCE_ASSERTION_HEADER = (
    "left_source",
    "right_source",
    "normalized_identifier",
    "network_scope",
    "instrument_id",
    "balance_kind",
    "left_location_id",
    "right_location_id",
    "left_quantity",
    "right_quantity",
    "quantity_difference",
    "status",
    "as_of_at",
    "as_of_precision",
    "notes",
)


@dataclass(frozen=True)
class BalanceInspectRecord:
    source: str
    input_mode: BalanceInputMode
    snapshot_origin: BalanceSnapshotOrigin
    target_count: int
    snapshot_count: int
    reference_row_count: int
    matched_reference_count: int
    missing_reference_count: int
    source_document_count: int = 0
    network_api_count: int = 0
    operator_assertion_count: int = 0
    cross_source_ready: BalanceCrossSourceReadyStatus = "not_applicable"
    offline_ready: BalanceOfflineReadyStatus = "no_balance_inputs"
    unexpected_superseded_output_count: int = 0
    min_target_date: str = ""
    max_target_date: str = ""
    min_reference_date: str = ""
    max_reference_date: str = ""

    def to_row(self) -> dict[str, str]:
        return {
            "source": self.source,
            "input_mode": self.input_mode,
            "snapshot_origin": self.snapshot_origin,
            "target_count": str(self.target_count),
            "snapshot_count": str(self.snapshot_count),
            "reference_row_count": str(self.reference_row_count),
            "matched_reference_count": str(self.matched_reference_count),
            "missing_reference_count": str(self.missing_reference_count),
            "source_document_count": str(self.source_document_count),
            "network_api_count": str(self.network_api_count),
            "operator_assertion_count": str(self.operator_assertion_count),
            "cross_source_ready": self.cross_source_ready,
            "offline_ready": self.offline_ready,
            "unexpected_superseded_output_count": str(
                self.unexpected_superseded_output_count
            ),
            "min_target_date": self.min_target_date,
            "max_target_date": self.max_target_date,
            "min_reference_date": self.min_reference_date,
            "max_reference_date": self.max_reference_date,
        }

    @classmethod
    def from_row(cls, row: dict[str, str]) -> BalanceInspectRecord:
        return cls(
            source=row["source"],
            input_mode=cast(BalanceInputMode, row["input_mode"]),
            snapshot_origin=cast(BalanceSnapshotOrigin, row["snapshot_origin"]),
            target_count=int(row["target_count"]),
            snapshot_count=int(row["snapshot_count"]),
            reference_row_count=int(row["reference_row_count"]),
            matched_reference_count=int(row["matched_reference_count"]),
            missing_reference_count=int(row["missing_reference_count"]),
            source_document_count=int(row["source_document_count"]),
            network_api_count=int(row["network_api_count"]),
            operator_assertion_count=int(row["operator_assertion_count"]),
            cross_source_ready=cast(
                BalanceCrossSourceReadyStatus, row["cross_source_ready"]
            ),
            offline_ready=cast(BalanceOfflineReadyStatus, row["offline_ready"]),
            unexpected_superseded_output_count=int(
                row["unexpected_superseded_output_count"]
            ),
            min_target_date=row["min_target_date"],
            max_target_date=row["max_target_date"],
            min_reference_date=row["min_reference_date"],
            max_reference_date=row["max_reference_date"],
        )


@dataclass(frozen=True)
class BalanceCheckSummaryRecord:
    source: str
    resolution_mode: BalanceResolutionMode
    check_status: BalanceCheckStatus
    assertion_count: int
    issue_count: int
    min_assertion_date: str
    max_assertion_date: str
    latest_clean_checked_date: str
    latest_resolved_reference_checked_date: str
    assertion_status_counts: tuple[tuple[str, int], ...]
    selected_reference_kind_counts: tuple[tuple[str, int], ...]
    issue_kind_counts: tuple[tuple[str, int], ...]
    not_runnable_reason: str = ""
    error_message: str = ""

    def to_row(self) -> dict[str, str]:
        return {
            "source": self.source,
            "resolution_mode": self.resolution_mode,
            "check_status": self.check_status,
            "not_runnable_reason": self.not_runnable_reason,
            "assertion_count": str(self.assertion_count),
            "issue_count": str(self.issue_count),
            "min_assertion_date": self.min_assertion_date,
            "max_assertion_date": self.max_assertion_date,
            "latest_clean_checked_date": self.latest_clean_checked_date,
            "latest_resolved_reference_checked_date": self.latest_resolved_reference_checked_date,
            "assertion_status_counts": json.dumps(
                dict(self.assertion_status_counts),
                sort_keys=True,
            ),
            "selected_reference_kind_counts": json.dumps(
                dict(self.selected_reference_kind_counts),
                sort_keys=True,
            ),
            "issue_kind_counts": json.dumps(
                dict(self.issue_kind_counts),
                sort_keys=True,
            ),
            "error_message": self.error_message,
        }

    @classmethod
    def from_row(cls, row: dict[str, str]) -> BalanceCheckSummaryRecord:
        return cls(
            source=row["source"],
            resolution_mode=cast(BalanceResolutionMode, row["resolution_mode"]),
            check_status=cast(BalanceCheckStatus, row["check_status"]),
            not_runnable_reason=row["not_runnable_reason"],
            assertion_count=int(row["assertion_count"]),
            issue_count=int(row["issue_count"]),
            min_assertion_date=row["min_assertion_date"],
            max_assertion_date=row["max_assertion_date"],
            latest_clean_checked_date=row["latest_clean_checked_date"],
            latest_resolved_reference_checked_date=row[
                "latest_resolved_reference_checked_date"
            ],
            assertion_status_counts=_load_counts(row["assertion_status_counts"]),
            selected_reference_kind_counts=_load_counts(
                row["selected_reference_kind_counts"]
            ),
            issue_kind_counts=_load_counts(row["issue_kind_counts"]),
            error_message=row["error_message"],
        )


@dataclass(frozen=True)
class BalanceReconciliationBlockerRecord:
    source: str
    blocker_kind: str
    blocker_count: int
    notes: str = ""

    def to_row(self) -> dict[str, str]:
        return {
            "source": self.source,
            "blocker_kind": self.blocker_kind,
            "blocker_count": str(self.blocker_count),
            "notes": self.notes,
        }


@dataclass(frozen=True)
class CrossSourceAssertionRecord:
    left_source: str
    right_source: str
    normalized_identifier: str
    network_scope: str
    instrument_id: str
    balance_kind: str
    left_location_id: str
    right_location_id: str
    left_quantity: str
    right_quantity: str
    quantity_difference: str
    status: str
    as_of_at: str
    as_of_precision: str
    notes: str = ""

    def to_row(self) -> dict[str, str]:
        return {
            "left_source": self.left_source,
            "right_source": self.right_source,
            "normalized_identifier": self.normalized_identifier,
            "network_scope": self.network_scope,
            "instrument_id": self.instrument_id,
            "balance_kind": self.balance_kind,
            "left_location_id": self.left_location_id,
            "right_location_id": self.right_location_id,
            "left_quantity": self.left_quantity,
            "right_quantity": self.right_quantity,
            "quantity_difference": self.quantity_difference,
            "status": self.status,
            "as_of_at": self.as_of_at,
            "as_of_precision": self.as_of_precision,
            "notes": self.notes,
        }


def _load_counts(value: str) -> tuple[tuple[str, int], ...]:
    payload = json.loads(value or "{}")
    return tuple(sorted((str(key), int(count)) for key, count in payload.items()))
