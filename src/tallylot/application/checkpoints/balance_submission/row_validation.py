"""Row-level validation helpers for manual balance submissions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from decimal import InvalidOperation

from tallylot.adapters.support import location_id_from_parts
from tallylot.domain.reconciliation import normalize_balance_confirmation_kind
from tallylot.domain.checkpoints import normalize_balance_kind
from tallylot.domain.temporal import TemporalPrecision, parse_temporal_precision
from tallylot.domain.value_objects import (
    parse_decimal,
    parse_temporal_value,
    parse_timestamp,
)

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


def validate_balance_confirmation_rows(
    rows: list[tuple[int, dict[str, str]]],
    *,
    expected_source: str,
    issues: list[BalanceSubmissionIssue],
) -> list[SubmittedBalanceConfirmationRow]:
    parsed_rows: list[SubmittedBalanceConfirmationRow] = []
    for row_number, row in rows:
        base = _validate_balance_like_row(
            BALANCE_CONFIRMATIONS_FILENAME,
            row_number,
            row,
            expected_source,
            issues,
        )
        confirmation_kind = row.get("confirmation_kind", "").strip()
        asserted_meaning = row.get("asserted_meaning", "").strip()
        reviewed_by = row.get("reviewed_by", "").strip()
        reviewed_at = row.get("reviewed_at", "").strip()
        reason = row.get("reason", "").strip()
        support_ref = row.get("support_ref", "").strip()
        row_valid = True
        for field_name, value in (
            ("confirmation_kind", confirmation_kind),
            ("asserted_meaning", asserted_meaning),
            ("reviewed_by", reviewed_by),
            ("reviewed_at", reviewed_at),
            ("reason", reason),
        ):
            if value:
                continue
            row_valid = False
            issues.append(
                BalanceSubmissionIssue(
                    file_name=BALANCE_CONFIRMATIONS_FILENAME,
                    row_number=str(row_number),
                    column_name=field_name,
                    issue_kind="missing_required_value",
                    message=(
                        "balance_confirmations.csv rows require a non-blank "
                        f"{field_name}."
                    ),
                )
            )
        normalized_kind: str | None = None
        if confirmation_kind:
            try:
                normalized_kind = normalize_balance_confirmation_kind(confirmation_kind)
            except ValueError as exc:
                row_valid = False
                issues.append(
                    BalanceSubmissionIssue(
                        file_name=BALANCE_CONFIRMATIONS_FILENAME,
                        row_number=str(row_number),
                        column_name="confirmation_kind",
                        issue_kind="invalid_confirmation_kind",
                        message=str(exc),
                    )
                )
        parsed_reviewed_at = _parse_reviewed_at(
            row_number=row_number,
            raw_reviewed_at=reviewed_at,
            issues=issues,
        )
        if normalized_kind == "external_support" and not support_ref:
            row_valid = False
            issues.append(
                BalanceSubmissionIssue(
                    file_name=BALANCE_CONFIRMATIONS_FILENAME,
                    row_number=str(row_number),
                    column_name="support_ref",
                    issue_kind="missing_required_value",
                    message=(
                        "balance_confirmations.csv external_support rows require "
                        "a non-blank support_ref."
                    ),
                )
            )
        if normalized_kind == "manual_assertion" and support_ref:
            row_valid = False
            issues.append(
                BalanceSubmissionIssue(
                    file_name=BALANCE_CONFIRMATIONS_FILENAME,
                    row_number=str(row_number),
                    column_name="support_ref",
                    issue_kind="unexpected_value",
                    message=(
                        "balance_confirmations.csv manual_assertion rows must "
                        "leave support_ref blank."
                    ),
                )
            )
        if (
            base is None
            or not row_valid
            or normalized_kind is None
            or parsed_reviewed_at is None
        ):
            continue
        parsed_rows.append(
            SubmittedBalanceConfirmationRow(
                source=base.source,
                account=base.account,
                wallet=base.wallet,
                instrument_id=base.instrument_id,
                quantity=base.quantity,
                as_of_at=base.as_of_at,
                as_of_precision=base.as_of_precision,
                balance_kind=base.balance_kind,
                confirmation_kind=normalized_kind,
                support_ref=support_ref,
                asserted_meaning=asserted_meaning,
                reviewed_by=reviewed_by,
                reviewed_at=parsed_reviewed_at,
                reason=reason,
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


def _parse_reviewed_at(
    *,
    row_number: int,
    raw_reviewed_at: str,
    issues: list[BalanceSubmissionIssue],
) -> datetime | None:
    if not raw_reviewed_at:
        return None
    try:
        return parse_timestamp(raw_reviewed_at)
    except ValueError as exc:
        issues.append(
            BalanceSubmissionIssue(
                file_name=BALANCE_CONFIRMATIONS_FILENAME,
                row_number=str(row_number),
                column_name="reviewed_at",
                issue_kind="invalid_timestamp",
                message=str(exc),
            )
        )
        return None
