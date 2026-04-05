"""Consistency checks for manual balance submission packages."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from tallylot.domain.temporal import TemporalPrecision

from .contracts import (
    BalanceSubmissionIssue,
    BalanceSubmissionRow,
    LocationInventorySubmissionRow,
    SubmittedBalanceConfirmationRow,
)
from .schema import (
    BALANCE_CONFIRMATIONS_FILENAME,
    BALANCES_FILENAME,
    LOCATION_INVENTORY_FILENAME,
)


@dataclass(frozen=True, order=True)
class _LogicalBalanceKey:
    source: str
    account: str
    wallet: str
    instrument_id: str
    quantity: Decimal
    as_of_at: datetime
    as_of_precision: TemporalPrecision
    balance_kind: str


def collect_duplicate_rows(
    *,
    file_name: str,
    rows: list[tuple[int, dict[str, str]]],
    fields: tuple[str, ...],
    issues: list[BalanceSubmissionIssue],
) -> None:
    seen: dict[tuple[str, ...], int] = {}
    for row_number, row in rows:
        key = tuple(row.get(field, "").strip() for field in fields)
        if not any(key):
            continue
        first_row = seen.get(key)
        if first_row is None:
            seen[key] = row_number
            continue
        issues.append(
            BalanceSubmissionIssue(
                file_name=file_name,
                row_number=str(row_number),
                column_name="",
                issue_kind="duplicate_row",
                message=f"Row duplicates the logical key first seen on row {first_row}.",
            )
        )


def collect_balance_confirmation_mismatches(
    balance_rows: tuple[BalanceSubmissionRow, ...],
    confirmation_rows: tuple[SubmittedBalanceConfirmationRow, ...],
    *,
    issues: list[BalanceSubmissionIssue],
) -> None:
    balance_counts = Counter(_logical_balance_key(row) for row in balance_rows)
    confirmation_counts = Counter(
        _logical_balance_key(row) for row in confirmation_rows
    )
    for key in sorted(balance_counts):
        if balance_counts[key] == 1 and confirmation_counts.get(key, 0) == 0:
            issues.append(
                BalanceSubmissionIssue(
                    file_name=BALANCES_FILENAME,
                    row_number="",
                    column_name="",
                    issue_kind="missing_matching_confirmation",
                    message=(
                        "Each balance row must have exactly one matching "
                        "balance_confirmations.csv row."
                    ),
                )
            )
    for key in sorted(confirmation_counts):
        if confirmation_counts[key] == 1 and balance_counts.get(key, 0) == 0:
            issues.append(
                BalanceSubmissionIssue(
                    file_name=BALANCE_CONFIRMATIONS_FILENAME,
                    row_number="",
                    column_name="",
                    issue_kind="orphan_confirmation",
                    message=(
                        "Each confirmation row must match exactly one balances.csv row."
                    ),
                )
            )


def collect_location_inventory_conflicts(
    rows: list[LocationInventorySubmissionRow],
    *,
    issues: list[BalanceSubmissionIssue],
) -> None:
    high_confidence_keys: dict[tuple[str, str, str], set[tuple[str, str, str]]] = {}
    for row in rows:
        if row.confidence.strip().lower() != "high":
            continue
        location_key = (row.source, row.account, row.wallet)
        identifier_key = (
            row.identifier_kind,
            row.identifier_value,
            row.network_scope,
        )
        high_confidence_keys.setdefault(location_key, set()).add(identifier_key)
    for source, account, wallet in sorted(high_confidence_keys):
        identifiers = high_confidence_keys[(source, account, wallet)]
        if len(identifiers) <= 1:
            continue
        issues.append(
            BalanceSubmissionIssue(
                file_name=LOCATION_INVENTORY_FILENAME,
                row_number="",
                column_name="confidence",
                issue_kind="conflicting_high_confidence_identity",
                message=(
                    "More than one high-confidence identity row maps to the same "
                    f"logical location {source}/{account}/{wallet}."
                ),
            )
        )


def _logical_balance_key(
    row: BalanceSubmissionRow | SubmittedBalanceConfirmationRow,
) -> _LogicalBalanceKey:
    return _LogicalBalanceKey(
        source=row.source,
        account=row.account,
        wallet=row.wallet,
        instrument_id=row.instrument_id,
        quantity=row.quantity,
        as_of_at=row.as_of_at,
        as_of_precision=row.as_of_precision,
        balance_kind=row.balance_kind,
    )
