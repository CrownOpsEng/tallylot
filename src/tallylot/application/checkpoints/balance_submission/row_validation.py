"""Row-level validation helpers for manual balance submissions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from decimal import InvalidOperation

from tallylot.adapters.support import location_id_from_parts
from tallylot.domain.checkpoints import normalize_balance_kind
from tallylot.domain.temporal import TemporalPrecision, parse_temporal_precision
from tallylot.domain.value_objects import parse_decimal, parse_temporal_value

from .contracts import (
    BalanceSubmissionIssue,
    BalanceSubmissionRow,
    LocationInventorySubmissionRow,
    SubmittedBalanceEvidenceRow,
)
from .schema import (
    BALANCE_EVIDENCE_FILENAME,
    BALANCES_FILENAME,
    LOCATION_INVENTORY_FILENAME,
)


@dataclass(frozen=True)
class _ValidatedBalanceLikeRow:
    source: str
    account: str
    wallet: str
    instrument_id: str
    quantity: Decimal
    as_of_at: datetime
    as_of_precision: TemporalPrecision
    balance_kind: str
    notes: str


def validate_balance_rows(
    rows: list[tuple[int, dict[str, str]]],
    *,
    expected_source: str,
    issues: list[BalanceSubmissionIssue],
) -> list[BalanceSubmissionRow]:
    parsed_rows: list[BalanceSubmissionRow] = []
    for row_number, row in rows:
        base = _validate_balance_like_row(
            BALANCES_FILENAME,
            row_number,
            row,
            expected_source,
            issues,
        )
        if base is None:
            continue
        parsed_rows.append(
            BalanceSubmissionRow(
                source=base.source,
                account=base.account,
                wallet=base.wallet,
                instrument_id=base.instrument_id,
                quantity=base.quantity,
                as_of_at=base.as_of_at,
                as_of_precision=base.as_of_precision,
                balance_kind=base.balance_kind,
                notes=base.notes,
            )
        )
    return parsed_rows


def validate_balance_evidence_rows(
    rows: list[tuple[int, dict[str, str]]],
    *,
    expected_source: str,
    issues: list[BalanceSubmissionIssue],
) -> list[SubmittedBalanceEvidenceRow]:
    parsed_rows: list[SubmittedBalanceEvidenceRow] = []
    for row_number, row in rows:
        base = _validate_balance_like_row(
            BALANCE_EVIDENCE_FILENAME,
            row_number,
            row,
            expected_source,
            issues,
        )
        evidence_ref = row.get("evidence_ref", "").strip()
        if not evidence_ref:
            issues.append(
                BalanceSubmissionIssue(
                    file_name=BALANCE_EVIDENCE_FILENAME,
                    row_number=str(row_number),
                    column_name="evidence_ref",
                    issue_kind="missing_required_value",
                    message="Evidence rows require a non-blank evidence_ref.",
                )
            )
        if base is None or not evidence_ref:
            continue
        parsed_rows.append(
            SubmittedBalanceEvidenceRow(
                source=base.source,
                account=base.account,
                wallet=base.wallet,
                instrument_id=base.instrument_id,
                quantity=base.quantity,
                as_of_at=base.as_of_at,
                as_of_precision=base.as_of_precision,
                balance_kind=base.balance_kind,
                evidence_ref=evidence_ref,
                notes=base.notes,
            )
        )
    return parsed_rows


def validate_location_inventory_rows(
    rows: list[tuple[int, dict[str, str]]],
    *,
    expected_source: str,
    issues: list[BalanceSubmissionIssue],
) -> list[LocationInventorySubmissionRow]:
    parsed_rows: list[LocationInventorySubmissionRow] = []
    for row_number, row in rows:
        required = {
            field: row.get(field, "").strip()
            for field in (
                "source",
                "account",
                "wallet",
                "identifier_kind",
                "identifier_value",
                "confidence",
            )
        }
        row_valid = True
        for field_name, value in required.items():
            if value:
                continue
            row_valid = False
            issues.append(
                BalanceSubmissionIssue(
                    file_name=LOCATION_INVENTORY_FILENAME,
                    row_number=str(row_number),
                    column_name=field_name,
                    issue_kind="missing_required_value",
                    message=f"Location inventory rows require a non-blank {field_name}.",
                )
            )
        if required["source"] and required["source"] != expected_source:
            row_valid = False
            issues.append(
                BalanceSubmissionIssue(
                    file_name=LOCATION_INVENTORY_FILENAME,
                    row_number=str(row_number),
                    column_name="source",
                    issue_kind="source_mismatch",
                    message=(
                        f"Location inventory row source {required['source']!r} does not match "
                        f"submission source {expected_source!r}."
                    ),
                )
            )
        if row_valid:
            try:
                location_id_from_parts(
                    required["source"],
                    required["account"],
                    required["wallet"],
                )
            except ValueError as exc:
                row_valid = False
                issues.append(
                    BalanceSubmissionIssue(
                        file_name=LOCATION_INVENTORY_FILENAME,
                        row_number=str(row_number),
                        column_name="wallet",
                        issue_kind="invalid_location_parts",
                        message=str(exc),
                    )
                )
        if not row_valid:
            continue
        parsed_rows.append(
            LocationInventorySubmissionRow(
                source=required["source"],
                account=required["account"],
                wallet=required["wallet"],
                identifier_kind=required["identifier_kind"],
                identifier_value=required["identifier_value"],
                network_scope=row.get("network_scope", "").strip(),
                controller=row.get("controller", "").strip(),
                confidence=required["confidence"],
                notes=row.get("notes", "").strip(),
            )
        )
    return parsed_rows


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
                message=(
                    f"Row duplicates the logical key first seen on row {first_row}."
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


def _validate_balance_like_row(
    file_name: str,
    row_number: int,
    row: dict[str, str],
    expected_source: str,
    issues: list[BalanceSubmissionIssue],
) -> _ValidatedBalanceLikeRow | None:
    required = {
        field: row.get(field, "").strip()
        for field in (
            "source",
            "account",
            "wallet",
            "instrument_id",
            "quantity",
            "as_of_at",
            "as_of_precision",
            "balance_kind",
        )
    }
    row_valid = True
    for field_name, value in required.items():
        if value:
            continue
        row_valid = False
        issues.append(
            BalanceSubmissionIssue(
                file_name=file_name,
                row_number=str(row_number),
                column_name=field_name,
                issue_kind="missing_required_value",
                message=f"{file_name} rows require a non-blank {field_name}.",
            )
        )
    if required["source"] and required["source"] != expected_source:
        row_valid = False
        issues.append(
            BalanceSubmissionIssue(
                file_name=file_name,
                row_number=str(row_number),
                column_name="source",
                issue_kind="source_mismatch",
                message=(
                    f"{file_name} row source {required['source']!r} does not match "
                    f"submission source {expected_source!r}."
                ),
            )
        )
    quantity = _parse_quantity(
        file_name=file_name,
        row_number=row_number,
        raw_quantity=required["quantity"],
        issues=issues,
    )
    precision = _parse_precision(
        file_name=file_name,
        row_number=row_number,
        raw_precision=required["as_of_precision"],
        issues=issues,
    )
    as_of_at = _parse_as_of_at(
        file_name=file_name,
        row_number=row_number,
        raw_as_of_at=required["as_of_at"],
        precision=precision,
        issues=issues,
    )
    if required["balance_kind"]:
        normalize_balance_kind(required["balance_kind"])
    if not row_valid or quantity is None or precision is None or as_of_at is None:
        return None
    return _ValidatedBalanceLikeRow(
        source=required["source"],
        account=required["account"],
        wallet=required["wallet"],
        instrument_id=required["instrument_id"],
        quantity=quantity,
        as_of_at=as_of_at,
        as_of_precision=precision,
        balance_kind=normalize_balance_kind(required["balance_kind"]),
        notes=row.get("notes", "").strip(),
    )


def _parse_quantity(
    *,
    file_name: str,
    row_number: int,
    raw_quantity: str,
    issues: list[BalanceSubmissionIssue],
) -> Decimal | None:
    if not raw_quantity:
        return None
    try:
        quantity = parse_decimal(raw_quantity)
    except (ArithmeticError, InvalidOperation, ValueError) as exc:
        issues.append(
            BalanceSubmissionIssue(
                file_name=file_name,
                row_number=str(row_number),
                column_name="quantity",
                issue_kind="invalid_decimal",
                message=f"Could not parse quantity as Decimal: {exc}",
            )
        )
        return None
    if quantity is not None:
        return quantity
    issues.append(
        BalanceSubmissionIssue(
            file_name=file_name,
            row_number=str(row_number),
            column_name="quantity",
            issue_kind="invalid_decimal",
            message="Could not parse quantity as Decimal.",
        )
    )
    return None


def _parse_precision(
    *,
    file_name: str,
    row_number: int,
    raw_precision: str,
    issues: list[BalanceSubmissionIssue],
) -> TemporalPrecision | None:
    if not raw_precision:
        return None
    precision = parse_temporal_precision(raw_precision)
    if precision is not None:
        return precision
    issues.append(
        BalanceSubmissionIssue(
            file_name=file_name,
            row_number=str(row_number),
            column_name="as_of_precision",
            issue_kind="invalid_precision",
            message=f"Unsupported as_of_precision {raw_precision!r}.",
        )
    )
    return None


def _parse_as_of_at(
    *,
    file_name: str,
    row_number: int,
    raw_as_of_at: str,
    precision: TemporalPrecision | None,
    issues: list[BalanceSubmissionIssue],
) -> datetime | None:
    if not raw_as_of_at or precision is None:
        return None
    try:
        return parse_temporal_value(raw_as_of_at, precision=precision)
    except ValueError as exc:
        issues.append(
            BalanceSubmissionIssue(
                file_name=file_name,
                row_number=str(row_number),
                column_name="as_of_at",
                issue_kind="invalid_timestamp",
                message=str(exc),
            )
        )
        return None
