"""Balance reconciliation artifact records."""

from __future__ import annotations

import json
from dataclasses import dataclass

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

BALANCE_INSPECT_HEADER = (
    "source",
    "inspect_status",
    "snapshot_count",
    "reference_count",
    "source_document_count",
    "network_api_count",
    "operator_assertion_count",
    "missing_reference_count",
    "min_snapshot_date",
    "max_snapshot_date",
    "min_reference_date",
    "max_reference_date",
)

BALANCE_CHECK_SUMMARY_HEADER = (
    "source",
    "check_status",
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
    inspect_status: str
    snapshot_count: int
    reference_count: int
    source_document_count: int = 0
    network_api_count: int = 0
    operator_assertion_count: int = 0
    missing_reference_count: int = 0
    min_snapshot_date: str = ""
    max_snapshot_date: str = ""
    min_reference_date: str = ""
    max_reference_date: str = ""

    def to_row(self) -> dict[str, str]:
        return {
            "source": self.source,
            "inspect_status": self.inspect_status,
            "snapshot_count": str(self.snapshot_count),
            "reference_count": str(self.reference_count),
            "source_document_count": str(self.source_document_count),
            "network_api_count": str(self.network_api_count),
            "operator_assertion_count": str(self.operator_assertion_count),
            "missing_reference_count": str(self.missing_reference_count),
            "min_snapshot_date": self.min_snapshot_date,
            "max_snapshot_date": self.max_snapshot_date,
            "min_reference_date": self.min_reference_date,
            "max_reference_date": self.max_reference_date,
        }

    @classmethod
    def from_row(cls, row: dict[str, str]) -> BalanceInspectRecord:
        return cls(
            source=row["source"],
            inspect_status=row["inspect_status"],
            snapshot_count=int(row["snapshot_count"]),
            reference_count=int(row["reference_count"]),
            source_document_count=int(row["source_document_count"]),
            network_api_count=int(row["network_api_count"]),
            operator_assertion_count=int(row["operator_assertion_count"]),
            missing_reference_count=int(row["missing_reference_count"]),
            min_snapshot_date=row["min_snapshot_date"],
            max_snapshot_date=row["max_snapshot_date"],
            min_reference_date=row["min_reference_date"],
            max_reference_date=row["max_reference_date"],
        )


@dataclass(frozen=True)
class BalanceCheckSummaryRecord:
    source: str
    check_status: str
    assertion_count: int
    issue_count: int
    min_assertion_date: str
    max_assertion_date: str
    latest_clean_checked_date: str
    latest_resolved_reference_checked_date: str
    assertion_status_counts: tuple[tuple[str, int], ...]
    selected_reference_kind_counts: tuple[tuple[str, int], ...]
    issue_kind_counts: tuple[tuple[str, int], ...]
    error_message: str = ""

    def to_row(self) -> dict[str, str]:
        return {
            "source": self.source,
            "check_status": self.check_status,
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
            check_status=row["check_status"],
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
